import logging
import os
import time
import zipfile
from datetime import UTC, datetime, timedelta

from flask import current_app, request, send_file
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource

from delivery.service import get_or_create_for_token, record_download_event
from extension.extension import db, limiter
from model.Application import Application
from model.download_delivery import DownloadDelivery
from model.Download_Record import DownloadRecord
from model.download_token import DownloadToken
from model.Raster_Data import RasterData
from model.Shp_Data import Shp
from utils.log_helper import log_action
from utils.metrics import record_download
from utils.required import ensure_owner_or_admin
from utils.time_fmt import utc_iso_z


def _resolve_existing_path(path_value):
    if not path_value:
        return None
    candidate = str(path_value).replace("\\", "/").strip()
    if candidate.startswith("file://"):
        candidate = candidate[7:]
    if os.path.exists(candidate):
        return os.path.abspath(candidate)
    if candidate.startswith("/"):
        local = os.path.join(os.path.dirname(current_app.root_path), candidate.lstrip("/"))
        if os.path.exists(local):
            return os.path.abspath(local)
    local = os.path.join(current_app.root_path, candidate.lstrip("/"))
    if os.path.exists(local):
        return os.path.abspath(local)
    return None


def _cleanup_old_cache(cache_dir, max_age_hours=1):
    """Delete cached zip files older than max_age_hours."""
    if not os.path.isdir(cache_dir):
        return
    cutoff = time.time() - max_age_hours * 3600
    try:
        for fname in os.listdir(cache_dir):
            fpath = os.path.join(cache_dir, fname)
            try:
                if os.path.isfile(fpath) and os.path.getmtime(fpath) < cutoff:
                    os.remove(fpath)
            except OSError:
                pass
    except Exception:
        pass


def _zip_shp_bundle(shp_path):
    base, _ = os.path.splitext(shp_path)
    candidates = []
    for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg", ".qix"]:
        companion = f"{base}{ext}"
        if os.path.exists(companion):
            candidates.append(companion)
    if not candidates:
        return None
    out_dir = os.path.join(current_app.root_path, "runtime", "download_cache")
    os.makedirs(out_dir, exist_ok=True)
    _cleanup_old_cache(out_dir)
    out_name = f"{os.path.basename(base)}.zip"
    out_path = os.path.join(out_dir, out_name)
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file in candidates:
            zf.write(file, arcname=os.path.basename(file))
    return out_path


def _resolve_download_file(app):
    candidate_paths = [app.watermark_path, app.data_url]
    shp = db.session.get(Shp, app.data_id)
    if shp:
        candidate_paths.extend([shp.shp_file_path, shp.url])
    raster = db.session.get(RasterData, app.data_id)
    if raster:
        candidate_paths.extend([raster.raster_file_path, raster.url])
    for path_value in candidate_paths:
        resolved = _resolve_existing_path(path_value)
        if not resolved or not os.path.isfile(resolved):
            continue
        ext = os.path.splitext(resolved)[1].lower()
        if ext == ".shp":
            zipped = _zip_shp_bundle(resolved)
            if zipped:
                return zipped
            continue
        return resolved
    return None


def _write_download_record_for(app, user_number, filename, delivery_id=None):
    """Server-side DownloadRecord for a completed download (audit trail).

    Shared by the token download flow (v3 and legacy) and the older
    ``emp_download_zip`` endpoint. Best effort only: a failed audit write must
    never burn a token or answer 500 for a download whose file was already
    validated — same discipline as ``_log_event`` ("evidence never blocks
    business"). The rollback keeps the session usable for the caller's
    subsequent commits.
    """
    try:
        record = DownloadRecord(
            application_id=app.id,
            delivery_id=delivery_id,
            data_id=app.data_id,
            data_name=app.data_name or "",
            download_user_number=user_number,
            download_time=datetime.now(UTC),
            download_ip=request.remote_addr,
            applicant_user_number=app.applicant_user_number,
            filename=filename,
            timestamp=datetime.now(UTC),
        )
        db.session.add(record)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logging.warning("download record write failed for application %s", app.id, exc_info=True)


def _write_download_record(app, token_record, filename):
    """Token-flow wrapper around :func:`_write_download_record_for`."""
    _write_download_record_for(app, token_record.user_number, filename, token_record.delivery_id)


class EmpDownloadZipResource(Resource):
    """
    下载审批通过的数据文件
    ---
    tags: [Download]
    security: [Bearer: []]
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [application_id]
          properties:
            application_id: {type: integer, description: 申请编号}
            data_id: {type: integer, description: 数据编号}
    responses:
      200: {description: 返回数据文件}
      403: {description: 无下载权限}
      404: {description: 文件不存在}
    """

    @jwt_required()
    @limiter.limit("30 per minute")
    def post(self):
        data = request.get_json() or {}
        app_id = data.get("application_id")
        data_id = data.get("data_id")
        app = db.session.get(Application, app_id)
        if not app or app.adm1_statu != True or app.adm2_statu != True:
            return {"status": False, "msg": "无下载权限"}, 403
        denial = ensure_owner_or_admin(app)
        if denial:
            return denial

        # Check if data has been recalled
        if app.is_recalled:
            return {"status": False, "msg": "该数据已被回收，无法下载"}, 403
        if not app.download_enabled:
            return {"status": False, "msg": "该数据已被禁用下载"}, 403

        file_path = _resolve_download_file(app)
        if file_path and os.path.exists(file_path):
            download_name = os.path.basename(file_path)
            log_action(
                app.applicant_user_number,
                app.applicant_name,
                "数据下载",
                "成功",
                f"app_id={app.id} data_alias={app.data_alias} file={download_name}",
            )
            identity = get_jwt_identity() or {}
            user_number = identity.get("number", "") if isinstance(identity, dict) else str(identity)
            _write_download_record_for(app, user_number, download_name)
            record_download()
            return send_file(file_path, as_attachment=True, download_name=download_name)
        return {"status": False, "msg": "文件不存在"}, 404


class RecordDownloadResource(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json() or {}
        identity = get_jwt_identity() or {}
        user_number = identity.get("number", "") if isinstance(identity, dict) else str(identity)
        app_id = data.get("application_id")
        if not app_id:
            return {"status": False, "msg": "缺少申请编号"}, 400
        app = db.session.get(Application, app_id)
        if not app:
            return {"status": False, "msg": "申请不存在"}, 404
        # A client must not be able to forge audit rows for someone else's
        # application by passing its id.
        denial = ensure_owner_or_admin(app)
        if denial:
            return denial
        # Client-supplied data_id/dataName are not authoritative: audit fields
        # come from the application row so a forged body cannot misattribute
        # the download (only the display filename may be client-provided).
        new_record = DownloadRecord(
            application_id=app.id,
            data_id=app.data_id,
            data_name=app.data_name or "",
            download_user_number=user_number,
            download_time=datetime.now(UTC),
            download_ip=request.remote_addr,
            applicant_user_number=app.applicant_user_number,
            filename=data.get("fileName") or app.data_name or f"data_{app.data_id}",
            timestamp=datetime.now(UTC),
        )
        db.session.add(new_record)
        db.session.commit()
        return {"status": True, "msg": "下载记录已保存"}, 200


class RequestDownloadTokenResource(Resource):
    """
    申请一次性下载令牌
    ---
    tags: [Download]
    security: [Bearer: []]
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [application_id]
          properties:
            application_id: {type: integer, description: 申请编号}
    responses:
      200: {description: 令牌创建或复用成功（含个性化交付信息）}
      403: {description: 申请未通过审批、数据已回收或已禁用下载}
      404: {description: 申请不存在}
      500: {description: 个性化交付生成失败}
    """

    @jwt_required()
    @limiter.limit("10 per minute")
    def post(self):
        identity = get_jwt_identity() or {}
        user_number = identity.get("number", "unknown")
        data = request.get_json() or {}
        app_id = data.get("application_id")

        if not app_id:
            return {"status": False, "msg": "缺少申请编号"}, 400

        app = db.session.get(Application, app_id)
        if not app:
            return {"status": False, "msg": "申请不存在"}, 404
        denial = ensure_owner_or_admin(app)
        if denial:
            return denial
        if app.adm1_statu is not True or app.adm2_statu is not True:
            return {"status": False, "msg": "该申请尚未通过审批"}, 403
        if app.is_recalled:
            return {"status": False, "msg": "该数据已被回收"}, 403
        if not app.download_enabled:
            return {"status": False, "msg": "该数据已被禁用下载"}, 403

        try:
            token, delivery, reused = get_or_create_for_token(app, user_number)
        except Exception:
            logging.error("personalize delivery failed for application %s", app_id, exc_info=True)
            # Details go to the server log only (no exception text in the API).
            return {"status": False, "msg": "个性化交付生成失败: 详见服务端日志"}, 500

        log_action(
            user_number,
            identity.get("username", "unknown"),
            "下载令牌申请",
            "成功",
            f"app_id={app_id} delivery={delivery.uuid} reused={reused}",
        )

        return {
            "status": True,
            "token": token.token,
            "expires_at": token.expires_at.isoformat(),
            "reused": reused,
            "delivery": {
                "uuid": delivery.uuid,
                "fingerprint_id": delivery.fingerprint_id,
                "status": delivery.status,
                "created_at": utc_iso_z(delivery.created_at),
                "artifact_root": delivery.artifact_root,
            },
        }, 200


class TokenDownloadResource(Resource):
    """
    使用令牌下载文件
    ---
    tags: [Download]
    parameters:
      - in: path
        name: download_token
        type: string
        required: true
        description: 下载令牌
    responses:
      200: {description: 返回数据文件}
      403: {description: 令牌已使用、已过期或数据已被回收}
      404: {description: 令牌无效、交付未就绪或文件不存在}
    """

    @limiter.limit("30 per minute")
    def get(self, download_token):
        token_record = DownloadToken.query.filter_by(token=download_token).first()
        if not token_record:
            return {"status": False, "msg": "下载链接无效"}, 404
        if token_record.is_used:
            return {"status": False, "msg": "下载链接已使用"}, 403
        expires_at = token_record.expires_at
        if expires_at is not None and expires_at.tzinfo is None:
            # DB DATETIME columns hold naive values that were written in UTC
            # (datetime.now(UTC)); attach UTC before comparing so aware/naive
            # never mix (same convention as admin_application_resource.py).
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at and expires_at < datetime.now(UTC):
            return {"status": False, "msg": "下载链接已过期"}, 403

        app = db.session.get(Application, token_record.application_id)
        if not app:
            return {"status": False, "msg": "申请不存在"}, 404
        if app.is_recalled:
            return {"status": False, "msg": "数据已被回收"}, 403
        # Parity with the recall gate: an admin disabling downloads must also
        # invalidate already-issued tokens, not just new token requests.
        if not app.download_enabled:
            return {"status": False, "msg": "该数据已被禁用下载"}, 403

        if token_record.delivery_id is not None:
            return self._deliver_personalized(token_record, app)
        return self._deliver_legacy(token_record, app)

    def _deliver_personalized(self, token_record, app):
        """v3 branch: serve the personalized artifact and write the audit trail."""
        delivery = db.session.get(DownloadDelivery, token_record.delivery_id)
        if delivery is None or delivery.status != "READY":
            return {"status": False, "msg": "交付不存在或尚未就绪"}, 404
        file_path = _resolve_existing_path(delivery.artifact_path)
        if not file_path or not os.path.isfile(file_path):
            return {"status": False, "msg": "文件不存在"}, 404
        if os.path.splitext(file_path)[1].lower() == ".shp":
            zipped = _zip_shp_bundle(file_path)
            if zipped:
                file_path = zipped

        download_name = os.path.basename(file_path)
        token_record.is_used = True
        db.session.commit()
        _write_download_record(app, token_record, download_name)
        # DownloadCompleted evidence — best effort, never blocks the download.
        try:
            record_download_event(delivery, request.remote_addr, download_name, token_record.token[:8])
        except Exception:
            logging.warning("download evidence event failed for delivery %s", delivery.uuid, exc_info=True)
        log_action(
            token_record.user_number,
            "",
            "令牌下载",
            "成功",
            f"app_id={app.id} delivery={delivery.uuid} token={token_record.token[:8]}...",
        )
        return send_file(file_path, as_attachment=True, download_name=download_name)

    def _deliver_legacy(self, token_record, app):
        """Legacy branch (delivery_id NULL): old resolution path + audit trail."""
        file_path = _resolve_download_file(app)
        if file_path and os.path.exists(file_path):
            token_record.is_used = True
            db.session.commit()
            download_name = os.path.basename(file_path)
            _write_download_record(app, token_record, download_name)
            log_action(
                token_record.user_number, "", "令牌下载", "成功", f"app_id={app.id} token={token_record.token[:8]}..."
            )
            return send_file(file_path, as_attachment=True, download_name=download_name)
        return {"status": False, "msg": "文件不存在"}, 404
