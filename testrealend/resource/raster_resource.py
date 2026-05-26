import base64
import io
import json
import logging
import os
from datetime import datetime

import qrcode
from flask import current_app, request, send_file
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
from utils.required import admin_required


class Adm1GetRasterApplicationsGenerateWatermark(Resource):
    @jwt_required()
    def get(self):
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("pageSize", 10, type=int)
        query = Application.query.filter(
            Application.adm1_statu == True, (Application.data_type == "raster") | (Application.data_type == None)
        )
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)
        items = [item.to_dict() for item in pagination.items]
        return {"status": True, "application_data": items, "pages": {"total": pagination.total}}, 200


class GenerateRasterWatermarkResource(Resource):
    @jwt_required()
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


def generate_raster_tiles(src_path, tiles_root, data_id, min_zoom=0, max_zoom=12):
    """Generate XYZ slippy-map tiles from a georeferenced raster file using GDAL.

    Only tiles that intersect the raster extent are generated, keeping the
    total count manageable even for high zoom levels.  Empty tiles (ocean or
    no-data regions outside the raster) are skipped.

    Returns a dict with ``{tile_count, zoom_range}`` for logging.
    """
    from osgeo import gdal

    src_ds = gdal.Open(src_path)
    if not src_ds:
        raise RuntimeError(f"Cannot open raster: {src_path}")

    warp_opts = gdal.WarpOptions(dstSRS="EPSG:3857", resampleAlg="bilinear", format="VRT")
    warped = gdal.Warp("", src_ds, options=warp_opts)
    if not warped:
        src_ds = None
        raise RuntimeError("Failed to reproject raster to EPSG:3857")

    gt = warped.GetGeoTransform()
    width = warped.RasterXSize
    height = warped.RasterYSize

    xmin = gt[0]
    ymax = gt[3]
    xmax = xmin + gt[1] * width
    ymin = ymax + gt[5] * height
    if ymin > ymax:
        ymin, ymax = ymax, ymin
    if xmin > xmax:
        xmin, xmax = xmax, xmin

    tile_size = 256
    origin_x = -20037508.34
    origin_y = 20037508.34
    total_tiles = 0

    for z in range(min_zoom, max_zoom + 1):
        n_tiles = 2**z
        res = (origin_y * 2.0) / (tile_size * n_tiles)

        tx_start = int((xmin - origin_x) / (tile_size * res))
        tx_end = int((xmax - origin_x) / (tile_size * res))
        ty_start = int((origin_y - ymax) / (tile_size * res))
        ty_end = int((origin_y - ymin) / (tile_size * res))

        tx_start = max(0, tx_start)
        tx_end = min(n_tiles - 1, tx_end)
        ty_start = max(0, ty_start)
        ty_end = min(n_tiles - 1, ty_end)

        for tx in range(tx_start, tx_end + 1):
            for ty in range(ty_start, ty_end + 1):
                tile_dir = os.path.join(tiles_root, str(data_id), str(z), str(tx))
                os.makedirs(tile_dir, exist_ok=True)
                out_path = os.path.join(tile_dir, f"{ty}.png")

                tile_xmin = origin_x + tx * tile_size * res
                tile_ymax = origin_y - ty * tile_size * res
                tile_xmax = tile_xmin + tile_size * res
                tile_ymin = tile_ymax - tile_size * res

                gdal.Translate(
                    out_path,
                    warped,
                    projWin=[tile_xmin, tile_ymax, tile_xmax, tile_ymin],
                    width=tile_size,
                    height=tile_size,
                    format="PNG",
                    outputType=gdal.GDT_Byte,
                )
                total_tiles += 1

    warped = None
    src_ds = None
    return {"tile_count": total_tiles, "zoom_range": f"{min_zoom}-{max_zoom}"}


class RasterGenerateTilesResource(Resource):
    """手动触发瓦片生成（用于已上传的栅格数据）"""

    @jwt_required()
    def post(self):
        data = request.get_json() or {}
        data_id = data.get("data_id")
        if not data_id:
            return {"status": False, "msg": "缺少 data_id"}, 400

        raster = db.session.get(RasterData, data_id)
        if not raster or not raster.raster_file_path:
            return {"status": False, "msg": "栅格数据不存在或路径无效"}, 404

        src_path = _resolve_existing_path(raster.raster_file_path)
        if not src_path:
            return {"status": False, "msg": "栅格文件在磁盘上不存在"}, 404

        tiles_root = os.path.join(current_app.config["UPLOAD_FOLDER"], "tiles")
        try:
            result = generate_raster_tiles(src_path, tiles_root, data_id)
            return {"status": True, "msg": f"瓦片生成完成，共 {result['tile_count']} 张", "data": result}, 200
        except Exception as e:
            logging.error("Tile generation failed: %s", e)
            return {"status": False, "msg": f"瓦片生成失败: {e!s}"}, 500


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
        tile_path = os.path.join(current_app.config["UPLOAD_FOLDER"], "tiles", str(data_id), f"{z}_{x}_{y}.png")
        if os.path.exists(tile_path):
            return send_file(tile_path, mimetype="image/png")
        return {"msg": "Tile not found"}, 404


class RasterEmbedDispatchResource(Resource):
    @jwt_required()
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
