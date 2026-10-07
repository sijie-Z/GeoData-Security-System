import base64
import io
import json
import logging
import os
import re
from datetime import date

from flask import current_app, request, send_file
from flask_jwt_extended import jwt_required
from flask_restful import Resource
from PIL import Image

from algorithm.embed import CapacityError
from algorithm.embed import embed as vector_embed
from algorithm.quality_metrics import compute_psnr
from algorithm.raster_blind_watermark import embed_blind
from algorithm.raster_dwt_watermark import embed_dwt
from algorithm.raster_histogram_watermark import embed_histogram
from algorithm.raster_iw_dct import embed_iw_dct
from algorithm.raster_reversible_watermark import embed_reversible
from extension.extension import db
from model.Application import Application
from model.Raster_Data import RasterData
from model.Shp_Data import Shp
from resource.watermark_utils import render_compact_qr
from utils.log_helper import log_action
from utils.required import admin_role_required


class Adm2GetEmbeddingWatermarkApplications(Resource):
    @admin_role_required("admin2")
    def get(self):
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("pageSize", 10, type=int)
        data_type = request.args.get("data_type", "vector").lower()

        # adm1 passed AND adm2 passed AND watermark generated
        query = Application.query.filter(
            Application.adm1_statu == True, Application.adm2_statu == True, Application.watermark_generated == True
        )

        if data_type:
            query = query.filter(Application.data_type == data_type)

        # feat_batch_embed: optional embed-state filter for the batch dialog
        # (?embedded=false -> not yet embedded; a NULL flag counts as not
        # embedded). Absent, the original single-embed list is unchanged.
        embedded = request.args.get("embedded")
        if embedded is not None:
            value = str(embedded).strip().lower()
            if value in ("false", "0", "no"):
                query = query.filter(
                    db.or_(Application.watermark_embedded == False, Application.watermark_embedded.is_(None))
                )
            elif value in ("true", "1", "yes"):
                query = query.filter(Application.watermark_embedded == True)

        pagination = query.paginate(page=page, per_page=page_size, error_out=False)

        items = [item.to_dict() for item in pagination.items]

        return {"status": True, "application_data": items, "pages": {"total": pagination.total}}, 200


def dispatch_embed_application(item, algorithm="lsb", action_prefix="", download=True):
    """Single-application watermark-embed dispatch, shared with the batch jobs.

    ``POST /api/embedding_watermark`` and the batch-embed job worker
    (``resource/batch_embed_resource.py``) both run through this one function,
    so the job path reuses the exact single-embed logic — algorithm dispatch,
    the blind compact-QR channel and the honest capacity errors. Returns
    ``(payload, status_code)``: 200 carries the send_file response (``download``
    True, the HTTP endpoint) or a small success dict (``download`` False, the
    worker — it has no request context and streams no file); any other code
    carries an error dict whose ``msg`` is client-readable. ``action_prefix``
    is prepended to the success audit action name (the job worker passes
    "批量" so entries read "批量矢量水印嵌入" / "批量栅格水印嵌入").
    """
    if not item.qrcode:
        return {"status": False, "msg": "水印尚未生成"}, 400

    try:
        data_type = (item.data_type or "vector").lower()

        if data_type == "raster":
            return _embed_raster(item, algorithm=algorithm, action_prefix=action_prefix, download=download)
        else:
            return _embed_vector(item, action_prefix=action_prefix, download=download)

    except CapacityError as e:
        # Readable 4xx instead of a generic 500 when the data has too few
        # vertices to carry the generated watermark.
        return {"status": False, "msg": str(e)}, 400
    except ValueError as e:
        # Raster algorithms raise ValueError for insufficient embedding
        # capacity, carrying the need-vs-available numbers ("Insufficient
        # histogram capacity: need N bits but peak bin has only M
        # pixels..."). Surface that readably like the vector path above;
        # anything else is a genuine server-side defect -> 500.
        if str(e).startswith("Insufficient"):
            return {"status": False, "msg": str(e)}, 400
        logging.error(str(e))
        return {"status": False, "msg": "操作失败，请稍后重试"}, 500
    except Exception as e:
        logging.error(str(e))
        return {"status": False, "msg": "操作失败，请稍后重试"}, 500


class EmbeddingWatermarkResource(Resource):
    """
    嵌入水印到数据文件
    ---
    tags: [Watermark]
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
      200: {description: 水印嵌入成功，返回带水印文件}
      400: {description: 水印尚未生成}
      404: {description: 申请或数据文件不存在}
    """

    @admin_role_required("admin2")
    def post(self):
        data = request.get_json()
        app_id = data.get("application_id")
        algorithm = data.get("algorithm", "lsb")

        item = db.session.get(Application, app_id)
        if not item:
            return {"status": False, "msg": "申请不存在"}, 404

        return dispatch_embed_application(item, algorithm=algorithm)


def _embed_vector(item, action_prefix="", download=True):
    """Embed the stored QR into the vector source; returns the zip (or a success
    dict when ``download`` is False — the batch worker has no HTTP response)."""
    shp_record = db.session.get(Shp, item.data_id)
    if not shp_record or not shp_record.shp_file_path:
        return {"status": False, "msg": f"未找到编号为 {item.data_id} 的矢量数据文件"}, 404

    shp_file = shp_record.shp_file_path
    if not os.path.exists(shp_file):
        candidate = os.path.join(current_app.root_path, shp_file.lstrip("/\\"))
        if os.path.exists(candidate):
            shp_file = candidate
        else:
            return {"status": False, "msg": "数据文件在服务器上丢失"}, 404

    temp_qr_path = os.path.join(current_app.config["UPLOAD_FOLDER"], "temp", f"qr_{item.id}.png")
    os.makedirs(os.path.dirname(temp_qr_path), exist_ok=True)
    with open(temp_qr_path, "wb") as fh:
        fh.write(base64.b64decode(item.qrcode))

    try:
        embed_result = vector_embed(shp_file, temp_qr_path)
        zip_path = embed_result["zip_path"]
        vr = embed_result["vr"]
    finally:
        if os.path.exists(temp_qr_path):
            try:
                os.remove(temp_qr_path)
            except OSError:
                pass

    item.watermark_embedded = True
    item.watermark_path = zip_path
    # Keep the extraction key material together: the mean coordinates (vr) and
    # the pixel size of the QR watermark that was actually embedded.
    item.vr_data = json.dumps({"vr": vr, "side_length": embed_result.get("side_length")})
    db.session.commit()

    cap = embed_result.get("capacity_report", {})
    log_action(
        item.applicant_user_number,
        item.applicant_name,
        f"{action_prefix}矢量水印嵌入",
        "成功",
        f"app_id={item.id} data_id={item.data_id} vertices={cap.get('total_vertices', 'N/A')} utilization={cap.get('utilization_percent', 'N/A')}%",
    )

    # 文件名: {数据名称}_申请_{申请ID}_{日期}_水印已嵌入.zip
    if not download:
        return {"status": True, "msg": "矢量水印嵌入成功", "data_type": "vector", "watermark_path": zip_path}, 200

    data_alias_safe = re.sub(r"[^\w\-一-鿿]", "_", item.data_alias or item.data_name or "data")
    today_str = date.today().isoformat()
    download_name = f"{data_alias_safe}_申请_{item.id}_{today_str}_水印已嵌入.zip"

    return send_file(zip_path, as_attachment=True, download_name=download_name)


def _embed_raster(item, algorithm="lsb", action_prefix="", download=True):
    """Embed the stored QR into the raster source; returns the stego file (or a
    success dict when ``download`` is False — the batch worker has no HTTP
    response)."""
    raster_record = db.session.get(RasterData, item.data_id)
    if not raster_record or not raster_record.raster_file_path:
        return {"status": False, "msg": f"未找到编号为 {item.data_id} 的栅格数据文件"}, 404

    host_path = raster_record.raster_file_path
    if not os.path.exists(host_path):
        candidate = os.path.join(current_app.root_path, host_path.lstrip("/\\"))
        if os.path.exists(candidate):
            host_path = candidate
        else:
            return {"status": False, "msg": "数据文件在服务器上丢失"}, 404

    if algorithm in ("blind", "blind_watermark", "iw_dct"):
        # The display QR bitmap (box_size=10) carries ~7 * 10^5 bits and can
        # never fit the blind/IW-DCT budget (~one bit per 8x8 host block);
        # embed a compact box_size=1 re-render of the stored QR text instead.
        # Honest boundary: ~81x81 px (6,561 bits) needs a >=1024x1024 host;
        # 512x512 (4,095 embeddable bits) still fails with a genuine
        # capacity 400.
        if not item.qr_text:
            return {
                "status": False,
                "msg": "该申请未记录二维码文本，无法使用盲水印 / IW-DCT；请重新生成水印后再试",
            }, 400
        qr_img = render_compact_qr(item.qr_text)
    else:
        qr_img = Image.open(io.BytesIO(base64.b64decode(item.qrcode))).convert("L")
    out_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "crmark", f"app_{item.id}")
    os.makedirs(out_dir, exist_ok=True)

    if algorithm == "dwt":
        result = embed_dwt(host_path=host_path, watermark_img=qr_img, output_dir=out_dir, prefix=f"app_{item.id}")
    elif algorithm == "histogram":
        result = embed_histogram(host_path=host_path, watermark_img=qr_img, output_dir=out_dir, prefix=f"app_{item.id}")
    elif algorithm == "iw_dct":
        result = embed_iw_dct(host_path=host_path, watermark_img=qr_img, output_dir=out_dir, prefix=f"app_{item.id}")
    elif algorithm in ("blind", "blind_watermark"):
        result = embed_blind(host_path=host_path, watermark_img=qr_img, output_dir=out_dir, prefix=f"app_{item.id}")
    else:
        result = embed_reversible(
            host_path=host_path, watermark_img=qr_img, output_dir=out_dir, prefix=f"app_{item.id}"
        )

    # Compute PSNR between original and stego
    psnr_value = None
    try:
        original_img = Image.open(host_path).convert("RGB")
        stego_img = Image.open(result["stego_path"]).convert("RGB")
        psnr_value = compute_psnr(original_img, stego_img)
    except Exception as e:
        logging.warning("PSNR computation failed: %s", e)

    item.watermark_embedded = True
    item.watermark_path = result["stego_path"]
    item.watermark_path_meta = result.get("wm_meta_path", "")
    item.watermark_path_map = result.get("wm_map_path", "")
    db.session.commit()

    psnr_str = f" psnr={psnr_value:.2f}dB" if psnr_value else ""
    log_action(
        item.applicant_user_number,
        item.applicant_name,
        f"{action_prefix}栅格水印嵌入",
        "成功",
        f"app_id={item.id} data_id={item.data_id} bit_count={result.get('bit_count', 'N/A')} changed={result.get('changed_count', 'N/A')}{psnr_str}",
    )

    if not download:
        return {
            "status": True,
            "msg": "栅格水印嵌入成功",
            "data_type": "raster",
            "watermark_path": result["stego_path"],
        }, 200

    data_alias_safe = re.sub(r"[^\w\-一-鿿]", "_", item.data_alias or item.data_name or "data")
    today_str = date.today().isoformat()
    download_name = f"{data_alias_safe}_申请_{item.id}_{today_str}_水印已嵌入.{os.path.basename(result['stego_path']).split('.')[-1]}"
    return send_file(result["stego_path"], as_attachment=True, download_name=download_name)
