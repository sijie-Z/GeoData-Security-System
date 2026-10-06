"""Robustness experiment matrix endpoints (admin).

``POST /api/robustness/run`` queues one (scheme x attack) matrix run against a
dataset's source shapefile. The run executes on a background thread (embedding
a large shapefile can take minutes); the API answers immediately with the
``run_id`` and the per-(scheme, attack) rows are pre-inserted with NULL metrics
that the worker updates in place — so ``GET /api/robustness/runs/<run_id>``
shows honest progress while the matrix is in flight, and ``GET
/api/robustness/runs`` lists recent runs grouped by ``run_id``.

Discipline:
  * one run at a time — a module lock rejects concurrent POSTs with 409;
  * the pure engine (``algorithm/robustness.py``) never touches Flask or the
    DB; this service layer is the only place that resolves the source file,
    builds the real v2 payload and persists rows;
  * a run that dies mid-flight stamps its still-pending rows with ``error``
    instead of leaving them looking "running" forever.
"""

import logging
import os
import secrets
import shutil
import tempfile
import threading
import uuid
from datetime import UTC, datetime

from flask import current_app, request
from flask_restful import Resource

from algorithm.robustness import ATTACK_DEFAULTS, run_matrix
from crypto.keys import ensure_active_key
from crypto.payload import build_qr_v2_text
from delivery.service import _classify_base, _resolve_existing_path
from extension.extension import db
from model.robustness_result import RobustnessResult
from model.Shp_Data import Shp
from utils.required import admin_required
from utils.time_fmt import utc_iso_z

ALLOWED_SCHEMES = ("legacy", "dqim1")
ALLOWED_ATTACKS = ("none", "translate", "scale", "vertex_drop", "noise", "simplify")
DEFAULT_SCHEMES = list(ALLOWED_SCHEMES)
DEFAULT_ATTACKS = list(ALLOWED_ATTACKS)
RUNS_PER_PAGE_DEFAULT = 10

# One matrix run at a time; held from worker spawn to completion.
_RUN_LOCK = threading.Lock()
# run_id -> Thread, so callers (tests) can join a run instead of polling.
_ACTIVE_RUNS = {}


def _resolve_vector_source(data_id, product_dir):
    """Resolve the source ``.shp`` for ``data_id`` (Shp table path).

    Same resolution rules as the download/delivery flow (``Shp.shp_file_path``
    then ``Shp.url``; a zip base is unpacked and its shapefile used). Returns
    None when there is no usable vector source.
    """
    shp = db.session.get(Shp, data_id)
    if shp is None:
        return None
    for path_value in (shp.shp_file_path, shp.url):
        resolved = _resolve_existing_path(path_value)
        if resolved and os.path.isfile(resolved):
            kind, payload = _classify_base(resolved, product_dir)
            if kind == "vector":
                return payload
    return None


def _stage_vector_source(shp_path, work_dir):
    """Copy the source shapefile + companions into ``work_dir``.

    The engine writes attacked/stego copies derived from its input paths;
    staging keeps every write away from the original upload folder.
    """
    stage_dir = os.path.join(work_dir, "source")
    os.makedirs(stage_dir, exist_ok=True)
    base = os.path.splitext(shp_path)[0]
    for ext in (".shp", ".shx", ".dbf", ".prj", ".cpg", ".qix"):
        src = base + ext
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(stage_dir, os.path.basename(src)))
    return os.path.join(stage_dir, os.path.basename(shp_path))


def _build_payload_text(data_id):
    """Real v2 signed payload (same chain as deliveries); random fid per run.

    The payload is labeled with the dataset id as its delivery field — it only
    names the experiment; nothing in the delivery tables is touched.
    """
    kid, _private_key = ensure_active_key()
    fid_hex = secrets.token_bytes(16).hex()
    return build_qr_v2_text(fid_hex, data_id, kid, int(datetime.now(UTC).timestamp()))


def _apply_rows(run_id, rows):
    """UPDATE the pre-inserted (scheme, attack) rows with measured metrics."""
    existing = {(r.scheme, r.attack): r for r in RobustnessResult.query.filter_by(run_id=run_id).all()}
    for row in rows:
        record = existing.get((row["scheme"], row["attack"]))
        if record is None:
            continue
        record.attack_params = row["attack_params"]
        record.nc = row["nc"]
        record.ber = row["ber"]
        record.decode_success = row["decode_success"]
        record.duration_ms = row["duration_ms"]
        record.error = row["error"] or None
    db.session.commit()


def _mark_run_error(run_id, exc):
    """Stamp an aborted run's still-pending rows so it cannot look 'running'."""
    message = f"run aborted: {exc}"[:255]
    for record in RobustnessResult.query.filter_by(run_id=run_id).all():
        if record.decode_success is None and record.nc is None and record.ber is None:
            record.error = message
    db.session.commit()


def _run_matrix_worker(app, run_id, base_shp, schemes, attacks, payload_text, work_dir):
    """Background worker: run the pure matrix engine, then persist the rows."""
    try:
        rows = run_matrix(base_shp, None, schemes, attacks, payload_text, work_dir)
        with app.app_context():
            _apply_rows(run_id, rows)
    except Exception as e:
        logging.exception("robustness run %s failed", run_id)
        try:
            with app.app_context():
                _mark_run_error(run_id, e)
        except Exception:
            logging.exception("robustness run %s: failed to stamp error rows", run_id)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
        _ACTIVE_RUNS.pop(run_id, None)
        _RUN_LOCK.release()


class RobustnessRunResource(Resource):
    """POST /api/robustness/run — queue one (scheme x attack) matrix run.

    body: ``{"data_id": int, "schemes": [...], "attacks": [...]}`` — schemes and
    attacks default to the full whitelists. Returns 202 + run_id immediately;
    the matrix itself runs on a background thread. 409 when a run is already
    in flight, 400 when the dataset has no resolvable vector source.
    """

    @admin_required
    def post(self):
        body = request.get_json(silent=True) or {}
        data_id = body.get("data_id")
        if not isinstance(data_id, int) or isinstance(data_id, bool):
            return {"status": False, "msg": "data_id 必须是整数"}, 400
        schemes = body.get("schemes") or DEFAULT_SCHEMES
        attacks = body.get("attacks") or DEFAULT_ATTACKS
        if not isinstance(schemes, list) or not schemes or not set(schemes) <= set(ALLOWED_SCHEMES):
            return {"status": False, "msg": f"schemes 仅支持 {list(ALLOWED_SCHEMES)}"}, 400
        if not isinstance(attacks, list) or not attacks or not set(attacks) <= set(ALLOWED_ATTACKS):
            return {"status": False, "msg": f"attacks 仅支持 {list(ALLOWED_ATTACKS)}"}, 400
        schemes = list(dict.fromkeys(schemes))
        attacks = list(dict.fromkeys(attacks))

        if not _RUN_LOCK.acquire(blocking=False):
            return {"status": False, "msg": "已有鲁棒性实验正在运行，请稍后再试"}, 409

        run_id = None
        worker_started = False
        work_dir = None
        try:
            app = current_app._get_current_object()
            work_dir = tempfile.mkdtemp(prefix="robustness_run_")
            source_shp = _resolve_vector_source(data_id, os.path.join(work_dir, "resolve"))
            if not source_shp:
                return {"status": False, "msg": f"未找到 data_id={data_id} 对应的矢量源文件"}, 400
            staged_shp = _stage_vector_source(source_shp, work_dir)
            payload_text = _build_payload_text(data_id)

            run_id = str(uuid.uuid4())
            created = datetime.now(UTC)
            for scheme in schemes:
                for attack in attacks:
                    db.session.add(
                        RobustnessResult(
                            run_id=run_id,
                            scheme=scheme,
                            attack=attack,
                            attack_params=dict(ATTACK_DEFAULTS[attack]),
                            data_ref=f"data_id={data_id}",
                            created_at=created,
                        )
                    )
            db.session.commit()

            worker = threading.Thread(
                target=_run_matrix_worker,
                args=(app, run_id, staged_shp, schemes, attacks, payload_text, work_dir),
                daemon=True,
            )
            _ACTIVE_RUNS[run_id] = worker
            worker.start()
            worker_started = True
        except Exception as e:
            db.session.rollback()
            logging.exception("failed to queue robustness run for data_id=%s", data_id)
            if run_id is not None:
                try:
                    _mark_run_error(run_id, e)
                except Exception:
                    db.session.rollback()
            return {"status": False, "msg": "创建鲁棒性实验失败"}, 500
        finally:
            if not worker_started:
                # Anything before a live worker (400 / 500 / start failure):
                # the lock never passes to a worker, so release it right here.
                _ACTIVE_RUNS.pop(run_id, None)
                if work_dir:
                    shutil.rmtree(work_dir, ignore_errors=True)
                _RUN_LOCK.release()

        return {
            "status": True,
            "msg": "实验已开始",
            "data": {"run_id": run_id, "total": len(schemes) * len(attacks)},
        }, 202


class RobustnessRunsResource(Resource):
    """GET /api/robustness/runs?page= — recent runs (grouped), newest first."""

    @admin_required
    def get(self):
        from sqlalchemy import case, func

        try:
            page = max(1, int(request.args.get("page", 1)))
        except (TypeError, ValueError):
            page = 1
        try:
            per_page = int(request.args.get("per_page", RUNS_PER_PAGE_DEFAULT))
        except (TypeError, ValueError):
            per_page = RUNS_PER_PAGE_DEFAULT
        per_page = min(max(1, per_page), 50)

        grouped = (
            db.session.query(
                RobustnessResult.run_id,
                func.min(RobustnessResult.created_at).label("created_at"),
                func.max(RobustnessResult.data_ref).label("data_ref"),
                func.count(RobustnessResult.id).label("total"),
                func.sum(case((RobustnessResult.decode_success.isnot(None), 1), else_=0)).label("done"),
                func.max(RobustnessResult.error).label("last_error"),
            )
            .group_by(RobustnessResult.run_id)
            .order_by(func.min(RobustnessResult.created_at).desc(), RobustnessResult.run_id.desc())
        )
        total_runs = grouped.count()
        page_rows = grouped.offset((page - 1) * per_page).limit(per_page).all()

        runs = [
            {
                "run_id": row.run_id,
                "created_at": utc_iso_z(row.created_at),
                "data_ref": row.data_ref,
                "total": int(row.total or 0),
                "done": int(row.done or 0),
                "error": row.last_error,
            }
            for row in page_rows
        ]
        return {"status": True, "runs": runs, "page": page, "per_page": per_page, "total_runs": int(total_runs)}, 200


class RobustnessRunDetailResource(Resource):
    """GET /api/robustness/runs/<run_id> — rows + progress for one run."""

    @admin_required
    def get(self, run_id):
        rows = RobustnessResult.query.filter_by(run_id=run_id).order_by(RobustnessResult.id.asc()).all()
        if not rows:
            return {"status": False, "msg": "实验不存在"}, 404
        done = sum(1 for row in rows if row.decode_success is not None)
        return {
            "status": True,
            "run": {
                "run_id": run_id,
                "data_ref": rows[0].data_ref,
                "created_at": utc_iso_z(rows[0].created_at),
                "done": done,
                "total": len(rows),
                "rows": [row.to_dict() for row in rows],
            },
        }, 200
