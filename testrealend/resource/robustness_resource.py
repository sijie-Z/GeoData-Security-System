"""Robustness experiment matrix endpoints (admin).

``POST /api/robustness/run`` queues one (scheme x attack x trial) matrix run
against a dataset's source shapefile. The run executes on a background thread
(embedding a large shapefile can take minutes); the API answers immediately
with the ``run_id`` and the per-cell rows are pre-inserted with NULL metrics
that the worker updates in place — so ``GET /api/robustness/runs/<run_id>``
shows honest progress while the matrix is in flight, and ``GET
/api/robustness/runs`` lists recent runs grouped by ``run_id``.

``trials`` (1-10, default 1) replicates every cell N times with fixed-seed
parameter sampling (see the engines); the row set per cell is bounded by
``MAX_MATRIX_ROWS`` (cells x trials <= 200, over-limit -> 400). The run detail
additionally carries a per-cell ``summary`` block (successes / success_rate /
mean_nc / std_nc over the non-null NCs).

Discipline:
  * one run at a time — a module lock rejects concurrent POSTs with 409;
  * before a new run is queued (which is the only moment no worker can be
    alive in this process), zombie runs are swept: runs whose every row is
    still pending with no error were killed by a backend restart, and their
    rows are stamped ``ZOMBIE_ERROR_MESSAGE`` so they show as interrupted
    instead of "running" forever;
  * the pure engines (``algorithm/robustness*.py``) never touch Flask or the
    DB; this service layer is the only place that resolves the source file,
    builds the real v2 payload and persists rows;
  * a run that dies mid-flight stamps its still-pending rows with ``error``
    instead of leaving them looking "running" forever.
"""

import inspect
import logging
import os
import secrets
import shutil
import tempfile
import threading
import uuid
from datetime import UTC, datetime
from statistics import mean, pstdev

from flask import current_app, request
from flask_restful import Resource

from algorithm.robustness import (
    ATTACK_DEFAULTS,
    RASTER_ATTACK_DEFAULTS,
    RASTER_ATTACKS,
    RASTER_SCHEMES,
    attack_noise,
    attack_scale,
    attack_simplify,
    attack_translate,
    attack_vertex_drop,
    make_host_tif,
    render_raster_payload_qr,
    run_matrix,
    run_raster_matrix,
)
from algorithm.robustness_raster import r_blur, r_crop, r_jpeg, r_noise, r_resize, r_rotate
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

# Multi-trial guard rails (feat_experiment_trials): 1-10 trials per cell and at
# most 200 pre-inserted rows per run (cells x trials, over-limit -> 400).
MIN_TRIALS = 1
MAX_TRIALS = 10
MAX_MATRIX_ROWS = 200

# Zombie sweep (Step 3b): a run whose worker died with the process (backend
# restart) keeps every row pending forever; the sweep stamps this message so
# list/detail status derivation renders it as interrupted, not "running".
ZOMBIE_ERROR_MESSAGE = "interrupted (no active worker)"

# Raster matrix (kind="raster"): a programmatically generated 512x512 GeoTIFF
# host, data_id ignored, same row schema. The reference raster matrix is
# 4 schemes x 6 attacks; "blur" is engine-supported and whitelisted but
# opt-in, so default runs mirror the taskbook matrix exactly.
RASTER_DATA_REF = "synthetic_512x512"
RASTER_DEFAULT_ATTACKS = ("none", "jpeg", "resize", "crop", "rotate", "noise")

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
    """UPDATE the pre-inserted (scheme, attack, trial) rows with measured metrics."""
    existing = {(r.scheme, r.attack, r.trial): r for r in RobustnessResult.query.filter_by(run_id=run_id).all()}
    for row in rows:
        record = existing.get((row["scheme"], row["attack"], row["trial"]))
        if record is None:
            continue
        record.attack_params = row["attack_params"]
        record.nc = row["nc"]
        record.ber = row["ber"]
        record.decode_success = row["decode_success"]
        record.duration_ms = row["duration_ms"]
        record.error = row["error"] or None
    db.session.commit()


def _sweep_zombie_runs(exclude_run_ids):
    """Stamp runs whose worker died with the process as interrupted (Step 3b).

    A zombie is a run whose every row is still pending (``decode_success IS
    NULL``) and carries no ``error`` — only a backend restart can produce that
    state, since a live worker either finishes, stamps its rows, or (on crash)
    ``_mark_run_error`` catches it. Called right after the run lock is
    acquired, when no worker can be alive in this process. Runs that made any
    progress, or already carry an error, are left alone; the sweep itself must
    never block a new experiment, so failures are logged and rolled back.
    """
    from sqlalchemy import case, func

    try:
        grouped = (
            db.session.query(RobustnessResult.run_id)
            .group_by(RobustnessResult.run_id)
            .having(func.sum(case((RobustnessResult.decode_success.isnot(None), 1), else_=0)) == 0)
            .having(func.sum(case((RobustnessResult.error.isnot(None), 1), else_=0)) == 0)
            .all()
        )
        zombie_ids = [run_id for (run_id,) in grouped if run_id not in exclude_run_ids]
        if not zombie_ids:
            return
        for record in RobustnessResult.query.filter(RobustnessResult.run_id.in_(zombie_ids)).all():
            record.error = ZOMBIE_ERROR_MESSAGE
        db.session.commit()
        logging.info("robustness zombie sweep: stamped %d run(s): %s", len(zombie_ids), zombie_ids)
    except Exception:
        db.session.rollback()
        logging.exception("robustness zombie sweep failed (continuing with the new run)")


def _build_summary(rows):
    """Per-(scheme, attack) aggregation block for the run detail.

    ``trials`` counts the cell's rows, ``successes`` the rows whose
    ``decode_success`` is true, ``success_rate = successes / trials``.
    ``mean_nc`` / ``std_nc`` are computed over the non-null NC values only
    (a null NC means "decode failed outright — nothing to compare");
    an all-null cell reports ``None`` for both. ``std_nc`` is the population
    standard deviation (ddof=0) of the same set.
    """
    buckets = {}
    order = []
    for row in rows:
        key = (row.scheme, row.attack)
        if key not in buckets:
            buckets[key] = {"scheme": row.scheme, "attack": row.attack, "trials": 0, "successes": 0, "ncs": []}
            order.append(key)
        bucket = buckets[key]
        bucket["trials"] += 1
        if row.decode_success:
            bucket["successes"] += 1
        if row.nc is not None:
            bucket["ncs"].append(float(row.nc))

    summary = []
    for key in order:
        bucket = buckets[key]
        ncs = bucket["ncs"]
        summary.append(
            {
                "scheme": bucket["scheme"],
                "attack": bucket["attack"],
                "trials": bucket["trials"],
                "successes": bucket["successes"],
                "success_rate": (bucket["successes"] / bucket["trials"]) if bucket["trials"] else None,
                "mean_nc": float(mean(ncs)) if ncs else None,
                "std_nc": float(pstdev(ncs)) if ncs else None,
            }
        )
    return summary


def _mark_run_error(run_id, exc):
    """Stamp an aborted run's still-pending rows so it cannot look 'running'."""
    message = f"run aborted: {exc}"[:255]
    for record in RobustnessResult.query.filter_by(run_id=run_id).all():
        if record.decode_success is None and record.nc is None and record.ber is None:
            record.error = message
    db.session.commit()


def _run_matrix_worker(app, run_id, base_shp, schemes, attacks, trials, payload_text, work_dir):
    """Background worker: run the pure matrix engine, then persist the rows."""
    try:
        rows = run_matrix(base_shp, None, schemes, attacks, payload_text, work_dir, trials=trials)
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


def _run_raster_matrix_worker(app, run_id, host_tif, schemes, attacks, trials, payload_qr_png, work_dir):
    """Background worker for kind="raster": run the raster engine, persist rows."""
    try:
        rows = run_raster_matrix(host_tif, schemes, attacks, payload_qr_png, work_dir, trials=trials)
        with app.app_context():
            _apply_rows(run_id, rows)
    except Exception as e:
        logging.exception("robustness raster run %s failed", run_id)
        try:
            with app.app_context():
                _mark_run_error(run_id, e)
        except Exception:
            logging.exception("robustness raster run %s: failed to stamp error rows", run_id)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
        _ACTIVE_RUNS.pop(run_id, None)
        _RUN_LOCK.release()


def _kind_from_data_ref(data_ref):
    """Run kind for list responses, inferred without a schema change.

    Raster runs record ``RASTER_DATA_REF`` ("synthetic..."), vector runs record
    ``data_id=<id>`` — the prefix is the discriminator.
    """
    return "raster" if str(data_ref or "").startswith("synthetic") else "vector"


class RobustnessRunResource(Resource):
    """POST /api/robustness/run — queue one (scheme x attack x trial) matrix run.

    body: ``{"kind": "vector"|"raster", "data_id": int, "schemes": [...],
    "attacks": [...], "trials": int}``. ``kind`` defaults to "vector"
    (backwards compatible): vector runs resolve the dataset's source shapefile;
    raster runs ignore ``data_id`` and embed into a programmatically generated
    512x512 GeoTIFF host (``data_ref="synthetic_512x512"``; with ``trials > 1``
    one host per trial, seed 7 + trial). Schemes and attacks default to the
    kind's whitelist. ``trials`` (1-10, default 1) replicates every cell N
    times; cross-cell totals are bounded by ``MAX_MATRIX_ROWS``. Returns 202 +
    run_id immediately; the matrix itself runs on a background thread. 409 when
    a run is already in flight (vector and raster share one lock), 400 when the
    dataset has no resolvable vector source, kind/schemes/attacks/trials are
    invalid, or cells x trials exceeds the row cap.
    """

    @admin_required
    def post(self):
        body = request.get_json(silent=True) or {}
        kind = body.get("kind", "vector")
        if kind not in ("vector", "raster"):
            return {"status": False, "msg": "kind 仅支持 vector / raster"}, 400

        trials = body.get("trials", 1)
        if isinstance(trials, bool) or not isinstance(trials, int) or not (MIN_TRIALS <= trials <= MAX_TRIALS):
            return {"status": False, "msg": f"trials 必须是 {MIN_TRIALS}-{MAX_TRIALS} 的整数"}, 400

        if kind == "vector":
            data_id = body.get("data_id")
            if not isinstance(data_id, int) or isinstance(data_id, bool):
                return {"status": False, "msg": "data_id 必须是整数"}, 400
            allowed_schemes, allowed_attacks = ALLOWED_SCHEMES, ALLOWED_ATTACKS
            default_attacks = DEFAULT_ATTACKS
            attack_defaults = ATTACK_DEFAULTS
        else:
            data_id = None
            allowed_schemes, allowed_attacks = RASTER_SCHEMES, RASTER_ATTACKS
            default_attacks = RASTER_DEFAULT_ATTACKS
            attack_defaults = RASTER_ATTACK_DEFAULTS

        schemes = body.get("schemes") or list(allowed_schemes)
        attacks = body.get("attacks") or list(default_attacks)
        if not isinstance(schemes, list) or not schemes or not set(schemes) <= set(allowed_schemes):
            return {"status": False, "msg": f"schemes 仅支持 {list(allowed_schemes)}"}, 400
        if not isinstance(attacks, list) or not attacks or not set(attacks) <= set(allowed_attacks):
            return {"status": False, "msg": f"attacks 仅支持 {list(allowed_attacks)}"}, 400
        schemes = list(dict.fromkeys(schemes))
        attacks = list(dict.fromkeys(attacks))

        cells = len(schemes) * len(attacks)
        if cells * trials > MAX_MATRIX_ROWS:
            return {
                "status": False,
                "msg": f"实验规模超限：格子数 × trials 不得超过 {MAX_MATRIX_ROWS}（当前 {cells} × {trials}）",
            }, 400

        if not _RUN_LOCK.acquire(blocking=False):
            return {"status": False, "msg": "已有鲁棒性实验正在运行，请稍后再试"}, 409

        run_id = None
        worker_started = False
        work_dir = None
        try:
            app = current_app._get_current_object()
            work_dir = tempfile.mkdtemp(prefix=f"robustness_{kind}_run_")
            # The lock is held and no worker of this process can be alive right
            # now — the only window where a run that is all-pending with no
            # error is certainly a zombie (backend restart killed its worker).
            _sweep_zombie_runs(set(_ACTIVE_RUNS))
            if kind == "vector":
                source_shp = _resolve_vector_source(data_id, os.path.join(work_dir, "resolve"))
                if not source_shp:
                    return {"status": False, "msg": f"未找到 data_id={data_id} 对应的矢量源文件"}, 400
                staged_shp = _stage_vector_source(source_shp, work_dir)
                payload_text = _build_payload_text(data_id)
                data_ref = f"data_id={data_id}"
            else:
                # trials > 1: the engine generates a fresh host per trial
                # (seed 7 + trial); a single-trial run keeps the caller host.
                host_tif = make_host_tif(os.path.join(work_dir, "host_512x512.tif")) if trials == 1 else None
                payload_text = _build_payload_text(0)
                payload_qr = os.path.join(work_dir, "payload_qr.png")
                render_raster_payload_qr(payload_text, payload_qr)
                data_ref = RASTER_DATA_REF

            run_id = str(uuid.uuid4())
            created = datetime.now(UTC)
            for scheme in schemes:
                for attack in attacks:
                    for trial in range(1, trials + 1):
                        db.session.add(
                            RobustnessResult(
                                run_id=run_id,
                                scheme=scheme,
                                attack=attack,
                                trial=trial,
                                attack_params=dict(attack_defaults[attack]),
                                data_ref=data_ref,
                                created_at=created,
                            )
                        )
            db.session.commit()

            if kind == "vector":
                worker_target = _run_matrix_worker
                worker_args = (app, run_id, staged_shp, schemes, attacks, trials, payload_text, work_dir)
            else:
                worker_target = _run_raster_matrix_worker
                worker_args = (app, run_id, host_tif, schemes, attacks, trials, payload_qr, work_dir)
            worker = threading.Thread(target=worker_target, args=worker_args, daemon=True)
            _ACTIVE_RUNS[run_id] = worker
            worker.start()
            worker_started = True
        except Exception as e:
            db.session.rollback()
            logging.exception("failed to queue robustness run for kind=%s data_id=%s", kind, data_id)
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
            "data": {"run_id": run_id, "total": cells * trials, "kind": kind, "trials": trials},
        }, 202


class RobustnessRunsResource(Resource):
    """GET /api/robustness/runs?page= — recent runs (grouped), newest first.

    Every run entry carries ``kind`` ("vector" | "raster"), inferred from the
    ``data_ref`` prefix (raster runs always record ``synthetic...``), and
    ``trials`` (the run's per-cell trial count; derived from the rows —
    legacy rows have NULL trial, so a pre-trials run reports 1).
    """

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
                func.max(RobustnessResult.trial).label("trials"),
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
                "kind": _kind_from_data_ref(row.data_ref),
                "trials": int(row.trials or 1),
                "total": int(row.total or 0),
                "done": int(row.done or 0),
                "error": row.last_error,
            }
            for row in page_rows
        ]
        return {"status": True, "runs": runs, "page": page, "per_page": per_page, "total_runs": int(total_runs)}, 200


class RobustnessRunDetailResource(Resource):
    """GET /api/robustness/runs/<run_id> — rows + progress + summary for one run.

    Keys are only ever added: rows keep the shared (scheme, attack, trial)
    schema, the run object carries ``kind`` ("vector" | "raster") derived from
    its schemes, ``trials`` (max row trial; legacy NULL rows count as 1) and
    the per-cell ``summary`` aggregation block (success rate + mean/std NC).
    """

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
                "kind": "raster" if rows[0].scheme in RASTER_SCHEMES else "vector",
                "created_at": utc_iso_z(rows[0].created_at),
                "trials": max((row.trial or 1) for row in rows),
                "done": done,
                "total": len(rows),
                "summary": _build_summary(rows),
                "rows": [row.to_dict() for row in rows],
            },
        }, 200


# --------------------------------------------------------------------------- #
# attack source metadata (feat_lab_v2)                                         #
# --------------------------------------------------------------------------- #

# Registries for the UI's "view attack code" drawer. Only the attack functions
# themselves (their real source, via inspect.getsource) and their documented
# default parameters are exposed — never embedding/extraction code or key
# material. ``none`` maps to no function: it is the baseline branch, and its
# entry explains that instead of pretending to be a function.
_VECTOR_ATTACK_FUNCTIONS = {
    "translate": attack_translate,
    "scale": attack_scale,
    "vertex_drop": attack_vertex_drop,
    "noise": attack_noise,
    "simplify": attack_simplify,
}
_RASTER_ATTACK_FUNCTIONS = {
    "jpeg": r_jpeg,
    "resize": r_resize,
    "crop": r_crop,
    "rotate": r_rotate,
    "noise": r_noise,
    "blur": r_blur,
}

# Honest placeholder for the "none" cell: there is no attack function to show,
# so the drawer explains the actual baseline behavior instead.
_NONE_ATTACK_CODE = (
    "# 无攻击（基准）：“none” 不调用任何攻击函数——\n"
    "# 嵌入后的数据原样进入提取 / 解码流程，作为整行矩阵的对照基准\n"
    '# （见引擎中 attack == "none" 的分支）。\n'
    "# Baseline: no attack runs; the embedded data goes to extraction as-is.\n"
)


def _attack_meta_entry(name, params_default, fn):
    """One drawer entry: name + documented defaults + the real function source."""
    if fn is None:
        description = "Baseline: the embedded data is extracted and decoded without any attack."
        code = _NONE_ATTACK_CODE
    else:
        description = (fn.__doc__ or "").strip().splitlines()[0]
        code = inspect.getsource(fn)
    return {
        "name": name,
        "params_default": dict(params_default or {}),
        "description": description,
        "code": code,
    }


class RobustnessAttacksMetaResource(Resource):
    """GET /api/robustness/attacks/meta — attack functions' real source (admin).

    Read-only feed for the lab's "view attack code" drawer: for every attack of
    both kinds it returns the documented default parameters and the *actual*
    source of the attack function the experiment executes (``inspect.getsource``
    of ``algorithm/robustness.py`` / ``algorithm/robustness_raster.py``). The
    ``none`` baseline has no function and carries an explanatory stub instead.
    Only attack functions are exposed — embedding/extraction and key material
    are never part of any snippet.
    """

    @admin_required
    def get(self):
        vector = [
            _attack_meta_entry(name, ATTACK_DEFAULTS.get(name, {}), _VECTOR_ATTACK_FUNCTIONS.get(name))
            for name in ALLOWED_ATTACKS
        ]
        raster = [
            _attack_meta_entry(name, RASTER_ATTACK_DEFAULTS.get(name, {}), _RASTER_ATTACK_FUNCTIONS.get(name))
            for name in RASTER_ATTACKS
        ]
        return {"status": True, "vector": vector, "raster": raster}, 200
