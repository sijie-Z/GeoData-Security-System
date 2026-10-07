"""Batch watermark-embed jobs (feat_batch_embed).

``POST /api/watermark/batch_embed_jobs`` queues one async batch job over
``application_ids`` (1..MAX_BATCH_ITEMS) and answers immediately with the job
uuid; a daemon thread then walks the pre-inserted ``BatchEmbedItem`` rows and
runs every application through the exact single-embed dispatch
(``resource.watermark_embed_resource.dispatch_embed_application``) — algorithm
dispatch, blind compact-QR channel and the honest capacity errors included.
``GET`` lists recent jobs and ``GET /<uuid>`` returns one job with its
per-item results (status / error; ``vr_data`` is never exposed).

Discipline (same pattern as ``resource/robustness_resource.py``):
  * one active job at a time — a DB status check rejects concurrent submits
    with 409 carrying the active job's uuid (in-process submits are also
    serialized by a module lock);
  * before a new job is queued, stale queued/running jobs (``updated_at``
    untouched for STALE_JOB_SECONDS — only a dead worker leaves that state)
    are swept into ``status="done"`` + ``error=ZOMBIE_ERROR_MESSAGE`` with
    their pending items stamped ``fail``, so they cannot block new jobs or
    look "running" forever;
  * a worker that aborts mid-flight stamps its still-pending items;

Failure of one item never stops the rest; every item writes an audit entry
(action "批量矢量水印嵌入" / "批量栅格水印嵌入", success logged by the shared
dispatch, failures logged here).
"""

import logging
import threading
import uuid as uuid_lib
from datetime import UTC, datetime

from flask import current_app, request
from flask_jwt_extended import get_jwt_identity
from flask_restful import Resource

from extension.extension import db
from model.Application import Application
from model.batch_embed_job import BatchEmbedItem, BatchEmbedJob
from resource.watermark_embed_resource import dispatch_embed_application
from utils.log_helper import log_action
from utils.required import admin_required
from utils.time_fmt import utc_iso_z

MAX_BATCH_ITEMS = 50
JOBS_PER_PAGE_DEFAULT = 20
JOBS_PER_PAGE_MAX = 50

# A queued/running job untouched for this long is a zombie: a live worker
# heartbeats ``updated_at`` before every item (see _process_batch_item_inner).
STALE_JOB_SECONDS = 600
ZOMBIE_ERROR_MESSAGE = "interrupted (no active worker)"

# Serializes job creation (sweep + active-check + insert) within this process;
# the authoritative single-active-job gate is the DB status check itself.
_SUBMIT_LOCK = threading.Lock()
# job uuid -> Thread, so callers (tests) can join a job instead of polling.
_ACTIVE_JOBS = {}


def _as_utc(value):
    """Normalize a DB datetime to aware UTC (SQLite/MySQL return naive ones)."""
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _job_action_name(data_type):
    return "批量栅格水印嵌入" if str(data_type or "").lower() == "raster" else "批量矢量水印嵌入"


def _sweep_stale_jobs(exclude_uuids):
    """Stamp long-stale queued/running jobs as interrupted (zombie self-heal).

    A live worker bumps the job's ``updated_at`` before every item, so a job
    untouched for STALE_JOB_SECONDS can only mean its worker died with the
    process (or its thread never started). Its still-pending items are stamped
    ``fail`` so the detail view stays honest. Called under the submit lock
    right before the active-job check — never blocks a new job; failures are
    logged and rolled back.
    """
    now = datetime.now(UTC)
    try:
        candidates = BatchEmbedJob.query.filter(BatchEmbedJob.status.in_(("queued", "running"))).all()
        swept = 0
        for job in candidates:
            if job.uuid in exclude_uuids:
                continue
            reference = _as_utc(job.updated_at or job.started_at or job.created_at)
            if reference is None or (now - reference).total_seconds() < STALE_JOB_SECONDS:
                continue
            job.status = "done"
            job.error = ZOMBIE_ERROR_MESSAGE
            job.finished_at = now
            job.updated_at = now
            for item in BatchEmbedItem.query.filter_by(job_id=job.id, status="pending").all():
                item.status = "fail"
                item.error = ZOMBIE_ERROR_MESSAGE
                item.updated_at = now
                job.done += 1
                job.fail += 1
            swept += 1
        if swept:
            db.session.commit()
            logging.info("batch embed zombie sweep: stamped %d job(s)", swept)
    except Exception:
        db.session.rollback()
        logging.exception("batch embed zombie sweep failed (continuing with the new job)")


def _mark_job_aborted(job_uuid, exc):
    """Stamp a job whose worker aborted so it cannot look 'running' forever."""
    job = BatchEmbedJob.query.filter_by(uuid=job_uuid).first()
    if job is None or job.status == "done":
        return
    message = f"job aborted: {exc}"[:255]
    job.status = "done"
    job.error = message
    job.finished_at = datetime.now(UTC)
    job.updated_at = job.finished_at
    for item in BatchEmbedItem.query.filter_by(job_id=job.id, status="pending").all():
        item.status = "fail"
        item.error = ZOMBIE_ERROR_MESSAGE
        item.updated_at = job.finished_at
        job.done += 1
        job.fail += 1
    db.session.commit()


def _stamp_item_failed(job_id, item_id, message, user_number="", username=""):
    """Mark one item failed, bump the job counters and write the failure audit."""
    db.session.rollback()  # drop any partial state the failed embed left behind
    item = db.session.get(BatchEmbedItem, item_id)
    job = db.session.get(BatchEmbedJob, job_id)
    if item is None or job is None:
        return
    message = str(message)[:500]
    if item.status == "pending":
        job.done += 1
        job.fail += 1
    item.status = "fail"
    item.error = message
    item.updated_at = datetime.now(UTC)
    db.session.commit()
    log_action(
        user_number,
        username,
        _job_action_name(item.data_type),
        "失败",
        f"app_id={item.application_id} {message}",
    )


def _process_batch_item_inner(job_id, item_id, algorithm):
    job = db.session.get(BatchEmbedJob, job_id)
    item = db.session.get(BatchEmbedItem, item_id)
    if job is None or item is None or item.status != "pending":
        return

    # Heartbeat before a possibly slow embed: a running job whose updated_at
    # goes untouched for STALE_JOB_SECONDS counts as dead (zombie sweep).
    job.updated_at = datetime.now(UTC)
    db.session.commit()

    app_row = db.session.get(Application, item.application_id)
    if app_row is None:
        _stamp_item_failed(job_id, item_id, "申请不存在")
        return

    # The one shared dispatch: identical to POST /api/embedding_watermark,
    # including the blind compact-QR channel. "批量" prefix keeps the audit
    # action names ("批量矢量水印嵌入" / "批量栅格水印嵌入"); download=False
    # because the worker has no request context to stream a file into.
    payload, code = dispatch_embed_application(app_row, algorithm=algorithm, action_prefix="批量", download=False)

    if code == 200:
        item = db.session.get(BatchEmbedItem, item_id)
        job = db.session.get(BatchEmbedJob, job_id)
        item.status = "ok"
        item.error = None
        item.updated_at = datetime.now(UTC)
        job.ok += 1
        job.done += 1
        db.session.commit()
        return

    message = payload.get("msg") if isinstance(payload, dict) else None
    _stamp_item_failed(
        job_id,
        item_id,
        message or "嵌入失败",
        user_number=app_row.applicant_user_number,
        username=app_row.applicant_name,
    )


def _process_batch_item(job_id, item_id, algorithm):
    """Per-item isolation: one crashing item must not stop the rest."""
    try:
        _process_batch_item_inner(job_id, item_id, algorithm)
    except Exception as e:
        logging.exception("batch embed job item %s crashed", item_id)
        try:
            _stamp_item_failed(job_id, item_id, f"item crashed: {e}")
        except Exception:
            db.session.rollback()
            logging.exception("failed to stamp crashed batch embed item %s", item_id)


def _run_batch_job_worker(app, job_uuid, algorithm):
    """Background worker: run every pending item through the single-embed dispatch."""
    try:
        with app.app_context():
            job = BatchEmbedJob.query.filter_by(uuid=job_uuid).first()
            if job is None:
                return
            job.status = "running"
            job.started_at = datetime.now(UTC)
            job.updated_at = job.started_at
            db.session.commit()

            item_ids = [
                row.id for row in BatchEmbedItem.query.filter_by(job_id=job.id).order_by(BatchEmbedItem.id.asc()).all()
            ]
            for item_id in item_ids:
                _process_batch_item(job.id, item_id, algorithm)

            job = BatchEmbedJob.query.filter_by(uuid=job_uuid).first()
            if job is not None and job.status != "done":
                job.status = "done"
                job.finished_at = datetime.now(UTC)
                job.updated_at = job.finished_at
                db.session.commit()
    except Exception as e:
        logging.exception("batch embed job %s failed", job_uuid)
        try:
            with app.app_context():
                db.session.rollback()
                _mark_job_aborted(job_uuid, e)
        except Exception:
            logging.exception("batch embed job %s: failed to stamp aborted state", job_uuid)
    finally:
        _ACTIVE_JOBS.pop(job_uuid, None)


class BatchEmbedJobsResource(Resource):
    """POST /api/watermark/batch_embed_jobs — queue one batch-embed job (admin).

    body: ``{"application_ids": [int, ...], "algorithm": "lsb"}`` — algorithm
    optional, passed through to the single-embed dispatch for raster items
    (e.g. ``"blind"`` uses the compact-QR channel); vector items follow the
    single vector path. Ids are de-duplicated; empty / non-integer / > 50
    ids -> 400. One active job at a time -> 409 with the active job's uuid in
    ``data.uuid`` (stale jobs are swept first). 202 echoes the new uuid.
    GET — recent jobs, newest first (page / per_page; default 20, max 50).
    """

    @admin_required
    def post(self):
        body = request.get_json(silent=True) or {}
        app_ids = body.get("application_ids")
        if not isinstance(app_ids, list) or not app_ids:
            return {"status": False, "msg": "缺少 application_ids 列表"}, 400

        normalized = []
        for value in app_ids:
            if isinstance(value, bool) or not isinstance(value, int):
                return {"status": False, "msg": "application_ids 必须是整数列表"}, 400
            if value not in normalized:
                normalized.append(value)
        if len(normalized) > MAX_BATCH_ITEMS:
            return {"status": False, "msg": f"单次批量嵌入最多 {MAX_BATCH_ITEMS} 项（当前 {len(normalized)}）"}, 400

        algorithm = body.get("algorithm") or "lsb"
        if not isinstance(algorithm, str):
            return {"status": False, "msg": "algorithm 必须是字符串"}, 400
        algorithm = algorithm.strip()[:32] or "lsb"

        if not _SUBMIT_LOCK.acquire(timeout=10):
            return {"status": False, "msg": "批量嵌入作业正在创建，请稍后重试"}, 409

        job = None
        worker_started = False
        try:
            _sweep_stale_jobs(set(_ACTIVE_JOBS))

            active = (
                BatchEmbedJob.query.filter(BatchEmbedJob.status.in_(("queued", "running")))
                .order_by(BatchEmbedJob.id.desc())
                .first()
            )
            if active is not None:
                return {
                    "status": False,
                    "msg": "已有批量嵌入作业进行中，请等待完成后再提交",
                    "data": {"uuid": active.uuid},
                }, 409

            identity = get_jwt_identity()
            created_by = identity.get("number") if isinstance(identity, dict) else identity
            app_object = current_app._get_current_object()
            now = datetime.now(UTC)
            job = BatchEmbedJob(
                uuid=str(uuid_lib.uuid4()),
                status="queued",
                algorithm=algorithm,
                total=len(normalized),
                done=0,
                ok=0,
                fail=0,
                created_by=str(created_by) if created_by else None,
                created_at=now,
                updated_at=now,
            )
            db.session.add(job)
            db.session.flush()  # assign job.id for the item FKs
            for app_id in normalized:
                app_row = db.session.get(Application, app_id)
                db.session.add(
                    BatchEmbedItem(
                        job_id=job.id,
                        application_id=app_id,
                        data_id=app_row.data_id if app_row else None,
                        data_type=app_row.data_type if app_row else None,
                        status="pending",
                    )
                )
            db.session.commit()

            worker = threading.Thread(
                target=_run_batch_job_worker,
                args=(app_object, job.uuid, algorithm),
                daemon=True,
                name=f"batch-embed-{job.uuid[:8]}",
            )
            _ACTIVE_JOBS[job.uuid] = worker
            worker.start()
            worker_started = True
        except Exception:
            db.session.rollback()
            logging.exception("failed to queue batch embed job")
            if job is not None and not worker_started:
                try:
                    _mark_job_aborted(job.uuid, "worker failed to start")
                except Exception:
                    db.session.rollback()
                    logging.exception("failed to stamp aborted batch embed job")
            return {"status": False, "msg": "创建批量嵌入作业失败"}, 500
        finally:
            _SUBMIT_LOCK.release()

        return {
            "status": True,
            "msg": "批量嵌入作业已开始",
            "data": {"uuid": job.uuid, "total": job.total, "algorithm": algorithm},
        }, 202

    @admin_required
    def get(self):
        try:
            page = max(1, int(request.args.get("page", 1)))
        except (TypeError, ValueError):
            page = 1
        try:
            per_page = int(request.args.get("per_page", JOBS_PER_PAGE_DEFAULT))
        except (TypeError, ValueError):
            per_page = JOBS_PER_PAGE_DEFAULT
        per_page = min(max(1, per_page), JOBS_PER_PAGE_MAX)

        query = BatchEmbedJob.query.order_by(BatchEmbedJob.id.desc())
        total_jobs = query.count()
        jobs = query.offset((page - 1) * per_page).limit(per_page).all()
        return {
            "status": True,
            "jobs": [job.to_dict() for job in jobs],
            "page": page,
            "per_page": per_page,
            "total_jobs": int(total_jobs),
        }, 200


class BatchEmbedJobDetailResource(Resource):
    """GET /api/watermark/batch_embed_jobs/<uuid> — job + per-item results (admin)."""

    @admin_required
    def get(self, job_uuid):
        job = BatchEmbedJob.query.filter_by(uuid=job_uuid).first()
        if job is None:
            return {"status": False, "msg": "作业不存在"}, 404

        items = BatchEmbedItem.query.filter_by(job_id=job.id).order_by(BatchEmbedItem.id.asc()).all()
        app_ids = {item.application_id for item in items}
        applications = {}
        if app_ids:
            for row in Application.query.filter(Application.id.in_(app_ids)).all():
                applications[row.id] = row

        payload = job.to_dict()
        payload["items"] = [
            {
                "application_id": item.application_id,
                "data_id": item.data_id,
                "data_alias": applications[item.application_id].data_alias
                if item.application_id in applications
                else None,
                "data_type": item.data_type
                or (applications[item.application_id].data_type if item.application_id in applications else None),
                "status": item.status,
                "error": item.error,
                "updated_at": utc_iso_z(item.updated_at),
            }
            for item in items
        ]
        return {"status": True, "job": payload}, 200
