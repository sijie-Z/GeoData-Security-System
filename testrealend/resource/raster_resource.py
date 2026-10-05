import base64
import io
import json
import logging
import os
from datetime import datetime

import qrcode
from flask import Response, current_app, request, send_file
from flask_jwt_extended import jwt_required
from flask_restful import Resource
from PIL import Image

from algorithm.raster_dwt_watermark import embed_dwt, extract_dwt, recover_dwt
from algorithm.raster_histogram_watermark import embed_histogram, extract_histogram, recover_histogram
from algorithm.raster_reversible_watermark import (
    decode_reversible,
    embed_reversible,
    recover_reversible,
)
from extension.extension import db
from model.Application import Application
from model.Raster_Data import RasterData
from resource.watermark_utils import build_qr_text, get_qr_version
from utils.required import admin_required, admin_role_required


def _ensure_proj_data_env():
    """Neutralize an incompatible PROJ data override before rasterio is imported.

    PostgreSQL/PostGIS installers (seen with PostgreSQL 14 / PostGIS 3.5) export
    user-level PROJ_LIB/GDAL_DATA pointing at an ancient proj.db
    (DATABASE.LAYOUT.VERSION.MINOR < 6). rasterio bundles its own PROJ data; an
    incompatible override makes every CRS lookup fail ("The EPSG code is unknown")
    and breaks rio_tiler at import time. Only a verifiably incompatible override is
    removed, so healthy environments (CI, Linux) are left untouched.
    """
    import sqlite3

    def _layout_minor_ok(proj_dir):
        db_path = os.path.join(proj_dir, "proj.db")
        if not os.path.isfile(db_path):
            return False
        try:
            con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            try:
                row = con.execute(
                    "SELECT value FROM metadata WHERE key = 'DATABASE.LAYOUT.VERSION.MINOR'"
                ).fetchone()
            finally:
                con.close()
            return row is not None and int(row[0]) >= 6
        except Exception:
            return False

    active = os.environ.get("PROJ_DATA") or os.environ.get("PROJ_LIB")
    if active and not _layout_minor_ok(active):
        os.environ.pop("PROJ_DATA", None)
        os.environ.pop("PROJ_LIB", None)
        logging.warning("Ignoring incompatible PROJ_LIB/PROJ_DATA %r - using rasterio's bundled PROJ data", active)


_ensure_proj_data_env()

# Note: imported below the guard on purpose — rasterio/PROJ read PROJ_* at import time.
from rasterio.errors import CRSError
from rio_tiler.errors import MissingCRS, TileOutsideBounds
from rio_tiler.io import Reader


class Adm1GetRasterApplicationsGenerateWatermark(Resource):
    @admin_role_required("admin1")
    def get(self):
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("pageSize", 10, type=int)
        query = Application.query.filter(
            Application.adm1_statu == True,
            Application.adm2_statu == True,
            Application.watermark_generated == False,
            (Application.data_type == "raster") | (Application.data_type == None),
        )
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)
        items = [item.to_dict() for item in pagination.items]
        return {"status": True, "application_data": items, "pages": {"total": pagination.total}}, 200


class GenerateRasterWatermarkResource(Resource):
    @admin_role_required("admin1")
    def post(self):
        data = request.get_json() or {}
        app_id = data.get("application_id")
        item = db.session.get(Application, app_id)
        if not item:
            return {"status": False, "msg": "申请不存在"}, 404

        if item.watermark_generated:
            return {"status": False, "msg": "水印已生成，请勿重复操作"}, 400

        try:
            qr_content, signature = build_qr_text(item, data)
            qr_version = get_qr_version(len(qr_content))
            qr = qrcode.QRCode(
                version=qr_version,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_content)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()

            item.qrcode = img_str
            item.watermark_generated = True
            item.qr_version = qr_version
            item.qr_signature = signature
            item.generation_timestamp = datetime.now()

            for field in ["purpose", "usage_scope", "security_level", "custom_tag"]:
                if data.get(field):
                    setattr(item, field, str(data.get(field)).strip())
            if data.get("reason"):
                item.reason = str(data.get("reason")).strip()

            db.session.commit()
            return {
                "status": True,
                "msg": "栅格水印生成成功",
                "qrcode": img_str,
                "qr_text": qr_content,
                "qr_version": qr_version,
                "signature": signature,
            }, 200
        except Exception as e:
            logging.error(str(e))
            return {"status": False, "msg": "操作失败，请稍后重试"}, 500


def _runtime_dir(*parts):
    path = os.path.join(current_app.root_path, "runtime", *parts)
    os.makedirs(path, exist_ok=True)
    return path


class RasterGenerateTilesResource(Resource):
    """预生成已退役：瓦片改为按需动态出图。保留端点以兼容旧前端调用（no-op）。"""

    @jwt_required()
    def post(self):
        return {"status": True, "message": "dynamic tiles enabled"}, 200


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


def _create_qrcode_base64(item):
    qr_content, signature = build_qr_text(item, {"reason": item.reason})
    qr_version = get_qr_version(len(qr_content))
    qr = qrcode.QRCode(
        version=qr_version,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_content)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    item.qr_version = qr_version
    item.qr_signature = signature
    item.generation_timestamp = datetime.now()
    return img_str


def _resolve_raster_source_path(item):
    candidates = [item.data_url, item.data_name]
    raster = db.session.get(RasterData, item.data_id)
    if raster:
        candidates.extend([raster.raster_file_path, raster.url, raster.name, raster.alias])
    for value in candidates:
        resolved = _resolve_existing_path(value)
        if resolved and os.path.isfile(resolved):
            return resolved
    return None


def _to_preview_base64(file_path):
    with Image.open(file_path) as img:
        img = img.convert("RGB")
        img.thumbnail((1024, 1024))
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()


class RasterPreviewResource(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json() or {}
        file_path = data.get("file_path")
        resolved = _resolve_existing_path(file_path)
        if not resolved or not os.path.isfile(resolved):
            return {"status": False, "message": "文件不存在或路径无效"}, 404
        try:
            img_str = _to_preview_base64(resolved)
            return {"status": True, "base64": img_str}, 200
        except Exception as e:
            logging.error(str(e))
            return {"status": False, "message": "操作失败，请稍后重试"}, 500


class RasterTilesResource(Resource):
    @jwt_required()
    def get(self, data_id, z, x, y):
        raster = db.session.get(RasterData, data_id)
        src_path = _resolve_existing_path(raster.raster_file_path) if raster else None
        if not src_path or not os.path.isfile(src_path):
            return {"msg": "Tile not found"}, 404

        try:
            with Reader(src_path) as reader:
                indexes = (1, 2, 3) if reader.dataset.count > 4 else None
                img = reader.tile(x, y, z, indexes=indexes)
            return Response(img.render(img_format="PNG"), mimetype="image/png")
        except TileOutsideBounds:
            return {"msg": "Tile out of range"}, 400
        except (CRSError, MissingCRS):
            return {"msg": "Raster has no usable coordinate reference system"}, 422
        except Exception:
            logging.error("Tile render failed for data_id=%s z=%s x=%s y=%s", data_id, z, x, y, exc_info=True)
            return {"msg": "Tile render failed"}, 500


class RasterEmbedDispatchResource(Resource):
    @admin_role_required("admin2")
    def post(self):
        data = request.get_json() or {}
        app_id = data.get("application_id")
        algorithm = data.get("algorithm", "lsb")
        item = db.session.get(Application, app_id)
        if not item:
            return {"status": False, "msg": "申请不存在"}, 404
        embed_resource = CRMarkEmbedResource()
        result, code = embed_resource._embed(item, algorithm=algorithm)
        if code == 200:
            return {"status": True, "msg": "栅格水印嵌入成功", "data": result}, 200
        return result, code


class CRMarkEmbedResource(Resource):
    def _embed(self, item, algorithm="lsb"):
        """内部方法，直接接收item对象，避免递归调用解析request。

        Args:
            item: Application model instance.
            algorithm: 'lsb' (default) or 'dwt'.
        """
        source_path = _resolve_raster_source_path(item)
        if not source_path:
            return {"status": False, "message": "未找到可用的栅格原始文件路径"}, 404
        if not item.qrcode:
            item.qrcode = _create_qrcode_base64(item)
            item.watermark_generated = True
        try:
            qr_img = Image.open(io.BytesIO(base64.b64decode(item.qrcode))).convert("L")
            out_dir = _runtime_dir("crmark", f"app_{item.id}")

            if algorithm == "dwt":
                result = embed_dwt(
                    host_path=source_path, watermark_img=qr_img, output_dir=out_dir, prefix=f"app_{item.id}"
                )
            elif algorithm == "histogram":
                result = embed_histogram(
                    host_path=source_path, watermark_img=qr_img, output_dir=out_dir, prefix=f"app_{item.id}"
                )
            else:
                result = embed_reversible(
                    host_path=source_path, watermark_img=qr_img, output_dir=out_dir, prefix=f"app_{item.id}"
                )

            item.watermark_embedded = True
            item.watermark_path = result["stego_path"]
            db.session.commit()

            response = {
                "status": True,
                "algorithm": algorithm,
                "stego_path": result["stego_path"],
                "wm_meta_path": result["wm_meta_path"],
                "stego_preview_base64": _to_preview_base64(result["stego_path"]),
            }
            # LSB stores a separate wm_map file; DWT stores everything in meta
            if "wm_map_path" in result:
                response["wm_map_path"] = result["wm_map_path"]
            return response, 200
        except Exception as e:
            db.session.rollback()
            logging.error(str(e))
            return {"status": False, "message": "操作失败，请稍后重试"}, 500

    @admin_required
    def post(self):
        data = request.get_json() or {}
        app_id = data.get("application_id")
        item = db.session.get(Application, app_id)
        if not item:
            return {"status": False, "message": "申请不存在"}, 404
        return self._embed(item)


class CRMarkRecoverResource(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json() or {}
        stego_path = _resolve_existing_path(data.get("stego_path"))
        wm_map_path = _resolve_existing_path(data.get("wm_map_path"))
        wm_meta_path = _resolve_existing_path(data.get("wm_meta_path"))
        if not stego_path:
            return {"status": False, "message": "缺少有效的 stego_path"}, 400
        if not wm_meta_path:
            return {"status": False, "message": "缺少有效的 wm_meta_path"}, 400

        # Detect algorithm from metadata
        algo = "lsb"
        try:
            with open(wm_meta_path, encoding="utf-8") as fp:
                meta_data = json.load(fp)
            algo = meta_data.get("algorithm", "lsb")
        except Exception:
            pass

        # For LSB, wm_map_path is also required
        if algo not in ("dwt", "histogram_shifting") and not wm_map_path:
            guessed_meta = os.path.splitext(wm_meta_path)[0].replace("_wm_meta", "_wm_map") + ".npz"
            wm_map_path = guessed_meta if os.path.exists(guessed_meta) else None
            if not wm_map_path:
                return {"status": False, "message": "缺少有效的 wm_map_path"}, 400
        try:
            output_dir = _runtime_dir("crmark", "recovered")
            out_name = f"recovered_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
            output_path = os.path.join(output_dir, out_name)
            if algo == "dwt":
                recover_dwt(stego_path, wm_meta_path, output_path)
            elif algo == "histogram_shifting":
                recover_histogram(stego_path, wm_meta_path, output_path)
            else:
                recover_reversible(stego_path, wm_map_path, wm_meta_path, output_path)
            return send_file(output_path, as_attachment=True, download_name="recovered_original.png")
        except Exception as e:
            logging.error(str(e))
            return {"status": False, "message": "操作失败，请稍后重试"}, 500


class CRMarkDecodeResource(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json() or {}
        stego_path = _resolve_existing_path(data.get("stego_path"))
        wm_meta_path = _resolve_existing_path(data.get("wm_meta_path"))
        if not stego_path or not wm_meta_path:
            return {"status": False, "message": "缺少有效的 stego_path 或 wm_meta_path"}, 400

        # Detect algorithm from metadata
        algo = "lsb"
        try:
            with open(wm_meta_path, encoding="utf-8") as fp:
                meta_data = json.load(fp)
            algo = meta_data.get("algorithm", "lsb")
        except Exception:
            pass

        try:
            output_dir = _runtime_dir("crmark", "decoded")
            out_name = f"decoded_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
            output_path = os.path.join(output_dir, out_name)
            if algo == "dwt":
                extract_dwt(stego_path, wm_meta_path, output_path)
            elif algo == "histogram_shifting":
                extract_histogram(stego_path, wm_meta_path, output_path)
            else:
                decode_reversible(stego_path, wm_meta_path, output_path)
            return send_file(output_path, as_attachment=True, download_name="decoded_watermark.png")
        except Exception as e:
            logging.error(str(e))
            return {"status": False, "message": "操作失败，请稍后重试"}, 500
