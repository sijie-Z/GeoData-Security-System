import os
import shutil
import time
import zipfile
from datetime import datetime

from flask import current_app, request, send_file
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity

from extension.extension import db, limiter
from model.Application import Application
from model.Download_Record import DownloadRecord
from model.download_token import DownloadToken
from model.Raster_Data import RasterData
from model.Shp_Data import Shp
from utils.log_helper import log_action
from datetime import datetime, timedelta


def _resolve_existing_path(path_value):
    if not path_value:
        return None
    candidate = str(path_value).replace('\\', '/').strip()
    if candidate.startswith('file://'):
        candidate = candidate[7:]
    if os.path.exists(candidate):
        return os.path.abspath(candidate)
    if candidate.startswith('/'):
        local = os.path.join(os.path.dirname(current_app.root_path), candidate.lstrip('/'))
        if os.path.exists(local):
            return os.path.abspath(local)
    local = os.path.join(current_app.root_path, candidate.lstrip('/'))
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
    for ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg', '.qix']:
        companion = f"{base}{ext}"
        if os.path.exists(companion):
            candidates.append(companion)
    if not candidates:
        return None
    out_dir = os.path.join(current_app.root_path, 'runtime', 'download_cache')
    os.makedirs(out_dir, exist_ok=True)
    _cleanup_old_cache(out_dir)
    out_name = f"{os.path.basename(base)}.zip"
    out_path = os.path.join(out_dir, out_name)
    with zipfile.ZipFile(out_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for file in candidates:
            zf.write(file, arcname=os.path.basename(file))
    return out_path


def _resolve_download_file(app):
    candidate_paths = [app.watermark_path, app.data_url]
    shp = Shp.query.get(app.data_id)
    if shp:
        candidate_paths.extend([shp.shp_file_path, shp.url])
    raster = RasterData.query.get(app.data_id)
    if raster:
        candidate_paths.extend([raster.raster_file_path, raster.url])
    for path_value in candidate_paths:
        resolved = _resolve_existing_path(path_value)
        if not resolved or not os.path.isfile(resolved):
            continue
        ext = os.path.splitext(resolved)[1].lower()
        if ext == '.shp':
            zipped = _zip_shp_bundle(resolved)
            if zipped:
                return zipped
            continue
        return resolved
    return None

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
        app_id = data.get('application_id')
        data_id = data.get('data_id')
        app = Application.query.get(app_id)
        if not app or app.adm1_statu != True or app.adm2_statu != True:
            return {'status': False, 'msg': '无下载权限'}, 403

        # Check if data has been recalled
        if app.is_recalled:
            return {'status': False, 'msg': '该数据已被回收，无法下载'}, 403
        if not app.download_enabled:
            return {'status': False, 'msg': '该数据已被禁用下载'}, 403

        file_path = _resolve_download_file(app)
        if file_path and os.path.exists(file_path):
            download_name = os.path.basename(file_path)
            log_action(
                app.applicant_user_number, app.applicant_name,
                '数据下载', '成功',
                f"app_id={app.id} data_alias={app.data_alias} file={download_name}"
            )
            return send_file(
                file_path,
                as_attachment=True,
                download_name=download_name
            )
        return {'status': False, 'msg': '文件不存在'}, 404

class RecordDownloadResource(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json() or {}
        user_number = data.get('applicant_user_number') or data.get('download_user_number', '')
        new_record = DownloadRecord(
            application_id=data.get('application_id'),
            data_id=data.get('data_id'),
            data_name=data.get('dataName', data.get('fileName') or f"data_{data.get('data_id')}"),
            download_user_number=user_number,
            download_time=datetime.utcnow(),
            download_ip=request.remote_addr,
            applicant_user_number=user_number,
            filename=data.get('fileName') or f"data_{data.get('data_id')}",
            timestamp=datetime.utcnow()
        )
        db.session.add(new_record)
        db.session.commit()
        return {'status': True, 'msg': '下载记录已保存'}, 200


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
      201: {description: 令牌创建成功}
      403: {description: 申请未通过审批或数据已回收}
      404: {description: 申请不存在}
    """
    @jwt_required()
    @limiter.limit("10 per minute")
    def post(self):
        identity = get_jwt_identity() or {}
        user_number = identity.get('number', 'unknown')
        data = request.get_json() or {}
        app_id = data.get('application_id')

        if not app_id:
            return {'status': False, 'msg': '缺少申请编号'}, 400

        app = Application.query.get(app_id)
        if not app:
            return {'status': False, 'msg': '申请不存在'}, 404
        if app.adm1_statu is not True or app.adm2_statu is not True:
            return {'status': False, 'msg': '该申请尚未通过审批'}, 403
        if app.is_recalled:
            return {'status': False, 'msg': '该数据已被回收'}, 403

        existing = DownloadToken.query.filter_by(
            application_id=app_id, user_number=user_number, is_used=False
        ).filter(DownloadToken.expires_at > datetime.utcnow()).first()
        if existing:
            return {
                'status': True,
                'token': existing.token,
                'expires_at': existing.expires_at.isoformat()
            }, 200

        token = DownloadToken(
            application_id=app_id,
            user_number=user_number,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db.session.add(token)
        db.session.commit()

        log_action(user_number, identity.get('username', 'unknown'),
                   '下载令牌申请', '成功', f"app_id={app_id}")

        return {
            'status': True,
            'token': token.token,
            'expires_at': token.expires_at.isoformat()
        }, 201


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
      403: {description: 令牌已使用或已过期}
      404: {description: 令牌无效或文件不存在}
    """
    @limiter.limit("30 per minute")
    def get(self, download_token):
        token_record = DownloadToken.query.filter_by(token=download_token).first()
        if not token_record:
            return {'status': False, 'msg': '下载链接无效'}, 404
        if token_record.is_used:
            return {'status': False, 'msg': '下载链接已使用'}, 403
        if token_record.expires_at and token_record.expires_at < datetime.utcnow():
            return {'status': False, 'msg': '下载链接已过期'}, 403

        app = Application.query.get(token_record.application_id)
        if not app:
            return {'status': False, 'msg': '申请不存在'}, 404

        file_path = _resolve_download_file(app)
        if file_path and os.path.exists(file_path):
            token_record.is_used = True
            db.session.commit()

            log_action(token_record.user_number, '',
                       '令牌下载', '成功',
                       f"app_id={app.id} token={download_token[:8]}...")

            return send_file(
                file_path,
                as_attachment=True,
                download_name=os.path.basename(file_path)
            )

        return {'status': False, 'msg': '文件不存在'}, 404
