"""Batch watermark-embed jobs (feat_batch_embed).

Covers the taskbook contract for the async batch-embed channel:

  * POST /api/watermark/batch_embed_jobs queues a job (202 + uuid) and a small
    real batch runs on the background worker -> the detail endpoint polls to
    done (2 applications: 1 success + 1 intentional failure — a data file that
    does not exist -> ok=1 fail=1, status done, done == total == ok + fail);
  * the job path REUSES the single-embed dispatch: a blind job embeds the
    compact QR on a 1024x1024 host (ok) while a 512x512 host lands its honest
    capacity 400 in ``item.error`` (job still done) — exactly the
    /api/embedding_watermark blind behavior;
  * one active job at a time -> 409 carrying the active job's uuid;
  * employee 403 / no token 401;
  * zombie self-heal: a stale running job (updated_at 30 min ago) is stamped
    ``interrupted (no active worker)`` when the next job is submitted;
  * every item writes an audit row with the batch action names.
"""

import base64
import io
import uuid
from datetime import UTC, datetime, timedelta

from tests.test_blind_compact import _make_geotiff, _read_meta, _seed_raster_app
from tests.test_watermark import _build_qr_png_b64, _build_roundtrip_shp, _create_vector_application, _signed_qr_text

BATCH_URL = "/api/watermark/batch_embed_jobs"


def _join_worker(job_uuid, timeout=240):
    import resource.batch_embed_resource as batch_embed_resource

    thread = batch_embed_resource._ACTIVE_JOBS.get(job_uuid)
    if thread is not None:
        thread.join(timeout=timeout)
        assert not thread.is_alive(), "batch embed worker did not finish in time"


def _submit(client, headers, app_ids, algorithm=None):
    body = {"application_ids": app_ids}
    if algorithm is not None:
        body["algorithm"] = algorithm
    return client.post(BATCH_URL, json=body, headers=headers)


def _detail(client, headers, job_uuid):
    resp = client.get(f"{BATCH_URL}/{job_uuid}", headers=headers)
    assert resp.status_code == 200, resp.get_data(as_text=True)
    return resp.get_json()["job"]


def _attach_qr(db, item, qr_text):
    """Persist a display bitmap + QR text so both dispatch branches are usable."""
    item.qrcode, _side = _build_qr_png_b64(qr_text)
    item.qr_text = qr_text
    item.watermark_generated = True
    db.session.commit()
    return item


def _missing_file_vector_app(db, alias):
    """An approved vector app whose Shp row does not exist -> deterministic item fail."""
    from model.Application import Application

    item = Application(
        data_id=999999,
        data_name=alias,
        data_alias=alias,
        data_type="vector",
        applicant_name="Tester",
        applicant_user_number="E001",
        reason="missing data file",
        adm1_statu=True,
        adm2_statu=True,
    )
    db.session.add(item)
    db.session.commit()
    # A QR is attached so the failure is the missing data file, not the QR guard.
    return _attach_qr(db, item, _signed_qr_text(item.id, alias))


class TestBatchEmbedAuthAndValidation:
    def test_no_token_401_and_employee_403(self, client, db, employee_headers):
        assert client.post(BATCH_URL, json={"application_ids": [1]}).status_code == 401
        assert client.get(BATCH_URL).status_code == 401

        resp = _submit(client, employee_headers, [1])
        assert resp.status_code == 403, resp.get_data(as_text=True)
        assert client.get(BATCH_URL, headers=employee_headers).status_code == 403

    def test_validation_rejects_bad_bodies(self, client, db, auth_headers):
        for bad in (None, {}, {"application_ids": []}, {"application_ids": "1"}, {"application_ids": [1, "2"]}):
            body = bad if bad is not None else {"nope": True}
            resp = client.post(BATCH_URL, json=body, headers=auth_headers)
            assert resp.status_code == 400, f"{body!r} must be rejected, got {resp.status_code}"

        over = {"application_ids": list(range(1, 52))}
        resp = client.post(BATCH_URL, json=over, headers=auth_headers)
        assert resp.status_code == 400
        assert "50" in resp.get_json()["msg"]

    def test_unknown_detail_404(self, client, db, auth_headers):
        resp = client.get(f"{BATCH_URL}/{uuid.uuid4()}", headers=auth_headers)
        assert resp.status_code == 404


class TestBatchEmbedRealRun:
    def test_two_apps_one_success_one_failure(self, client, db, auth_headers, tmp_path):
        """The real thing: background job, polled detail, ok=1 fail=1, audit rows."""
        from model.Application import Application
        from model.Log_Info import LogInfo

        shp_path = _build_roundtrip_shp(tmp_path, n_lines=20, n_pts=300)
        alias = f"be-ok-{uuid.uuid4().hex[:8]}"
        ok_app = _create_vector_application(db, shp_path, alias)
        _attach_qr(db, ok_app, _signed_qr_text(ok_app.id, alias))
        bad_app = _missing_file_vector_app(db, f"be-bad-{uuid.uuid4().hex[:8]}")

        resp = _submit(client, auth_headers, [ok_app.id, bad_app.id])
        assert resp.status_code == 202, resp.get_data(as_text=True)
        data = resp.get_json()["data"]
        assert data["total"] == 2
        job_uuid = data["uuid"]
        _join_worker(job_uuid)

        job = _detail(client, auth_headers, job_uuid)
        assert job["status"] == "done"
        assert job["total"] == job["done"] == 2
        assert job["ok"] + job["fail"] == job["total"]
        assert (job["ok"], job["fail"]) == (1, 1)

        items = {item["application_id"]: item for item in job["items"]}
        assert items[ok_app.id]["status"] == "ok"
        assert items[ok_app.id]["error"] is None
        assert items[ok_app.id]["data_alias"] == alias
        assert items[ok_app.id]["data_type"] == "vector"
        assert items[bad_app.id]["status"] == "fail"
        assert "未找到编号为 999999" in items[bad_app.id]["error"]

        # The successful item really embedded + persisted vr_data (not exposed by the API).
        db.session.expire_all()
        ok_row = db.session.get(Application, ok_app.id)
        assert ok_row.watermark_embedded is True
        assert ok_row.vr_data
        assert db.session.get(Application, bad_app.id).watermark_embedded is not True
        assert "vr_data" not in items[ok_app.id]

        # Both items wrote audit rows under the batch action names.
        actions = {
            (row.action, row.status)
            for row in LogInfo.query.filter(
                LogInfo.action == "批量矢量水印嵌入", LogInfo.details.like(f"%app_id={ok_app.id} %")
            ).all()
        }
        assert ("批量矢量水印嵌入", "成功") in actions
        bad_actions = {
            (row.action, row.status)
            for row in LogInfo.query.filter(LogInfo.details.like(f"%app_id={bad_app.id} %")).all()
        }
        assert ("批量矢量水印嵌入", "失败") in bad_actions

        # The job shows up in the recent-jobs list with its counts.
        listing = client.get(BATCH_URL, headers=auth_headers).get_json()
        assert listing["status"] is True
        listed = next(entry for entry in listing["jobs"] if entry["uuid"] == job_uuid)
        assert listed["status"] == "done"
        assert (listed["total"], listed["done"], listed["ok"], listed["fail"]) == (2, 2, 1, 1)

    def test_active_job_409_carries_uuid(self, client, db, auth_headers):
        from model.batch_embed_job import BatchEmbedJob

        active_uuid = str(uuid.uuid4())
        active = BatchEmbedJob(
            uuid=active_uuid,
            status="running",
            algorithm="lsb",
            total=1,
            done=0,
            ok=0,
            fail=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.session.add(active)
        db.session.commit()
        try:
            resp = _submit(client, auth_headers, [1])
            assert resp.status_code == 409, resp.get_data(as_text=True)
            body = resp.get_json()
            assert body["data"]["uuid"] == active_uuid
        finally:
            # Don't leave an active job blocking the other tests in the session DB.
            active.status = "done"
            active.updated_at = datetime.now(UTC)
            db.session.commit()


class TestBatchEmbedBlindReusesSinglePath:
    """algorithm passthrough: the job path must hit the same compact-QR channel."""

    def test_blind_1024_ok_512_capacity_error(self, client, db, auth_headers, tmp_path):
        from model.Application import Application
        from resource.watermark_utils import build_qr_text
        from tests.test_blind_compact import _compact_qr_side

        # Production payload (build_qr_text, ~447 bytes) — its compact re-render
        # is ~81x81 px: fits a 1024x1024 host, overflows a 512x512 one, exactly
        # like the /api/embedding_watermark blind tests pin.
        host_1024 = _make_geotiff(tmp_path / "job_host_1024.tif", 1024)
        big_app, _ = _seed_raster_app(db, host_1024, f"job-blind-1024-{uuid.uuid4().hex[:6]}")
        qr_text_big, _sig = build_qr_text(big_app, {"reason": "job blind 1024"})
        _attach_qr(db, big_app, qr_text_big)

        host_512 = _make_geotiff(tmp_path / "job_host_512.tif", 512)
        small_app, _ = _seed_raster_app(db, host_512, f"job-blind-512-{uuid.uuid4().hex[:6]}")
        qr_text_small, _sig2 = build_qr_text(small_app, {"reason": "job blind 512"})
        _attach_qr(db, small_app, qr_text_small)
        expected_side = _compact_qr_side(qr_text_big)
        assert expected_side * expected_side > 4096, "precondition: compact QR must overflow a 512 host"

        resp = _submit(client, auth_headers, [big_app.id, small_app.id], algorithm="blind")
        assert resp.status_code == 202, resp.get_data(as_text=True)
        job_uuid = resp.get_json()["data"]["uuid"]
        assert resp.get_json()["data"]["algorithm"] == "blind"
        _join_worker(job_uuid)

        job = _detail(client, auth_headers, job_uuid)
        assert job["status"] == "done"
        assert (job["ok"], job["fail"]) == (1, 1)
        items = {item["application_id"]: item for item in job["items"]}
        assert items[big_app.id]["status"] == "ok"
        assert items[small_app.id]["status"] == "fail"
        assert items[small_app.id]["error"].startswith("Insufficient blind watermark capacity")
        assert "1024" in items[small_app.id]["error"]

        # The embedded bitmap is the compact re-render (not the display render).
        db.session.expire_all()
        row = db.session.get(Application, big_app.id)
        meta = _read_meta(row.watermark_path_meta)
        assert meta["algorithm"] == "blind_watermark"
        assert meta["watermark"]["width"] == expected_side
        assert meta["watermark"]["height"] == expected_side


class TestBatchEmbedZombieSweep:
    def test_stale_running_job_stamped_interrupted(self, client, db, auth_headers):
        from model.batch_embed_job import BatchEmbedItem, BatchEmbedJob

        stale_uuid = str(uuid.uuid4())
        stale_time = datetime.now(UTC) - timedelta(minutes=30)
        stale = BatchEmbedJob(
            uuid=stale_uuid,
            status="running",
            algorithm="lsb",
            total=1,
            done=0,
            ok=0,
            fail=0,
            created_at=stale_time,
            started_at=stale_time,
            updated_at=stale_time,
        )
        db.session.add(stale)
        db.session.flush()
        db.session.add(
            BatchEmbedItem(job_id=stale.id, application_id=1, data_id=1, data_type="vector", status="pending")
        )
        db.session.commit()

        # A new submission sweeps the zombie first, then queues normally.
        bad_app = _missing_file_vector_app(db, f"be-zombie-{uuid.uuid4().hex[:8]}")
        resp = _submit(client, auth_headers, [bad_app.id])
        assert resp.status_code == 202, resp.get_data(as_text=True)
        new_uuid = resp.get_json()["data"]["uuid"]
        assert new_uuid != stale_uuid
        _join_worker(new_uuid)

        db.session.expire_all()
        zombie = BatchEmbedJob.query.filter_by(uuid=stale_uuid).first()
        assert zombie.status == "done"
        assert zombie.error == "interrupted (no active worker)"
        assert zombie.finished_at is not None
        assert zombie.done == 1 and zombie.fail == 1
        zombie_items = BatchEmbedItem.query.filter_by(job_id=zombie.id).all()
        assert [item.status for item in zombie_items] == ["fail"]
        assert zombie_items[0].error == "interrupted (no active worker)"
