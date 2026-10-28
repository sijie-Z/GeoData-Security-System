import base64
import hashlib
import io
import json
import logging
import os
from datetime import UTC, datetime, timedelta

import numpy as np
import qrcode
from flask import current_app, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource
from PIL import Image
from sqlalchemy import case, func
from werkzeug.utils import secure_filename

from algorithm.embed import embed as vector_embed
from algorithm.quality_metrics import compute_ber, compute_nc, compute_psnr, compute_ssim_simple
from algorithm.raster_reversible_watermark import embed_reversible
from extension.extension import db
from model.Application import Application
from model.Raster_Data import RasterData
from model.Shp_Data import Shp
from model.watermark_verification import WatermarkVerification
from resource.watermark_utils import (
    build_qr_text,
    get_qr_version,
)
from utils.log_helper import log_action
from utils.metrics import record_watermark
from utils.required import admin_required, admin_role_required, ensure_owner_or_admin


def _optional_form(name, max_len):
    """Optional form field → trimmed value or None, clamped to the column length."""
    value = (request.form.get(name) or "").strip()
    return value[:max_len] if value else None


def _parse_iso_dt(raw):
    """ISO date/time string → naive UTC datetime, or None when unparseable.

    Timezone-aware input is converted to UTC; naive input is treated as UTC
    (the storage convention of the DATETIME columns).
    """
    try:
        dt = datetime.fromisoformat(raw.strip())
    except (AttributeError, ValueError):
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC).replace(tzinfo=None)
    return dt


_APP_PRELOAD_CHUNK = 500


def _preload_applications(app_ids):
    """One IN query per 500 ids → ``{id: Application}`` (keeps SQLite/MySQL
    parameter limits safe for unusually large batches)."""
    app_map = {}
    for start in range(0, len(app_ids), _APP_PRELOAD_CHUNK):
        chunk = app_ids[start : start + _APP_PRELOAD_CHUNK]
        app_map.update({row.id: row for row in Application.query.filter(Application.id.in_(chunk)).all()})
    return app_map


class UploadOriginalWatermarkResource(Resource):
    """Upload original watermark image for a specific application."""

    @admin_required
    def post(self):
        if "file" not in request.files:
            return {"status": False, "msg": "没有上传文件"}, 400
        file = request.files["file"]
        if file.filename == "":
            return {"status": False, "msg": "没有选择文件"}, 400
        app_id = request.form.get("application_id")
        if not app_id:
            return {"status": False, "msg": "缺少申请编号"}, 400

        item = db.session.get(Application, app_id)
        if not item:
            return {"status": False, "msg": "申请不存在"}, 404

        try:
            filename = secure_filename(file.filename)
            save_dir = os.path.join(current_app.config["WATERMARK_FOLDER"], "original")
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, f"app_{item.id}_{filename}")
            file.save(save_path)

            item.watermark_path_map = save_path
            db.session.commit()

            identity = get_jwt_identity() or {}
            log_action(
                identity.get("number", "unknown"),
                identity.get("username", "unknown"),
                "上传原始水印",
                "成功",
                f"app_id={item.id}",
            )
            return {"status": True, "msg": "原始水印上传成功", "path": save_path}, 200
        except Exception as e:
            logging.error(str(e))
            return {"status": False, "msg": "上传失败"}, 500


class UploadExtractedWatermarkResource(Resource):
    """Upload extracted watermark image and compute NC against original."""

    @admin_required
    def post(self):
        if "file" not in request.files:
            return {"status": False, "msg": "没有上传文件"}, 400
        file = request.files["file"]
        if file.filename == "":
            return {"status": False, "msg": "没有选择文件"}, 400
        app_id = request.form.get("application_id")
        if not app_id:
            return {"status": False, "msg": "缺少申请编号"}, 400

        item = db.session.get(Application, app_id)
        if not item:
            return {"status": False, "msg": "申请不存在"}, 404

        try:
            filename = secure_filename(file.filename)
            save_dir = os.path.join(current_app.config["EXTRACTED_FOLDER"], "uploaded")
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, f"app_{item.id}_{filename}")
            file.save(save_path)

            # Compute NC if original watermark exists
            nc_value = None
            if item.qrcode:
                try:
                    original_img = Image.open(io.BytesIO(base64.b64decode(item.qrcode))).convert("L")
                    extracted_img = Image.open(save_path).convert("L").resize(original_img.size)
                    orig_bits = (np.array(original_img) > 127).astype(int).flatten()
                    extr_bits = (np.array(extracted_img) > 127).astype(int).flatten()
                    nc_value = compute_nc(orig_bits, extr_bits)
                    # Real quality metrics alongside NC: BER over the binarized
                    # bit arrays, SSIM between the two watermark images.
                    ber_value = compute_ber(orig_bits, extr_bits)
                    ssim_value = None
                    try:
                        ssim_value = round(compute_ssim_simple(original_img, extracted_img), 6)
                    except Exception as e:
                        logging.warning("SSIM computation failed: %s", e)

                    # Persist verification. psnr stays NULL here: this handler
                    # only sees the two watermark images, not the host/stego
                    # pair a PSNR would compare.
                    verification = WatermarkVerification(
                        application_id=app_id,
                        data_id=item.data_id,
                        data_type=item.data_type or "vector",
                        nc_value=round(nc_value, 6),
                        algorithm=_optional_form("algorithm", 32),
                        ssim=ssim_value,
                        ber=round(ber_value, 6),
                        delivery_uuid=_optional_form("delivery_uuid", 36),
                        fingerprint_id=_optional_form("fingerprint_id", 32),
                        host_type=_optional_form("host_type", 16),
                        original_hash=hashlib.sha256(item.qrcode.encode()).hexdigest(),
                        extracted_hash=hashlib.sha256(
                            base64.b64encode(open(save_path, "rb").read()).decode().encode()
                        ).hexdigest(),
                        verified_by=get_jwt_identity().get("number", "unknown")
                        if isinstance(get_jwt_identity(), dict)
                        else "unknown",
                        verified_at=datetime.now(UTC),
                        ip_address=request.remote_addr,
                    )
                    db.session.add(verification)
                    db.session.commit()
                except Exception as e:
                    logging.warning("NC computation failed: %s", e)

            identity = get_jwt_identity() or {}
            log_action(
                identity.get("number", "unknown") if isinstance(identity, dict) else "unknown",
                identity.get("username", "unknown") if isinstance(identity, dict) else "unknown",
                "上传提取水印",
                "成功",
                f"app_id={item.id} nc={nc_value}",
            )

            result = {"status": True, "msg": "提取水印上传成功", "path": save_path}
            if nc_value is not None:
                result["nc_value"] = round(nc_value, 6)
            return result, 200
        except Exception as e:
            logging.error(str(e))
            return {"status": False, "msg": "上传失败"}, 500


class UploadOriAndExtWatermarkResource(Resource):
    """
    上传原始水印与提取水印进行比对
    ---
    tags: [Watermark]
    security: [Bearer: []]
    consumes: [multipart/form-data]
    parameters:
      - in: formData
        name: originalFile
        type: file
        required: true
        description: 原始水印图片
      - in: formData
        name: extractedFile
        type: file
        required: true
        description: 提取的水印图片
    responses:
      200: {description: 比对完成，返回NC值}
      400: {description: 缺少文件}
    """

    @admin_required
    def post(self):
        original_file = request.files.get("originalFile")
        extracted_file = request.files.get("extractedFile")
        if not original_file or not extracted_file:
            return {"status": False, "msg": "缺少文件"}, 400

        # Optional application_id for looking up data_type
        app_id = request.form.get("application_id", type=int)
        data_type = None
        if app_id:
            app_item = db.session.get(Application, app_id)
            if app_item:
                data_type = app_item.data_type

        try:
            ori_img = Image.open(original_file.stream).convert("L")
            ext_img = Image.open(extracted_file.stream).convert("L").resize(ori_img.size)
            ori_arr = (np.array(ori_img) > 127).astype(np.uint8)
            ext_arr = (np.array(ext_img) > 127).astype(np.uint8)
            nc_value = float((ori_arr == ext_arr).sum() / ori_arr.size)
            # Real quality metrics alongside NC. compute_ber/SSIM work on the
            # flat bit arrays / watermark images; psnr stays NULL (no
            # host/stego pair available in this handler).
            ber_value = compute_ber(ori_arr.flatten(), ext_arr.flatten())
            ssim_value = None
            try:
                ssim_value = round(compute_ssim_simple(ori_img, ext_img), 6)
            except Exception as e:
                logging.warning("SSIM computation failed: %s", e)

            original_file.stream.seek(0)
            extracted_file.stream.seek(0)
            ori_b64 = base64.b64encode(original_file.read()).decode("utf-8")
            ext_b64 = base64.b64encode(extracted_file.read()).decode("utf-8")

            identity = get_jwt_identity() or {}

            # Persist verification result for forensic traceability
            verification = WatermarkVerification(
                application_id=app_id,
                data_type=data_type or "vector",
                nc_value=round(nc_value, 6),
                algorithm=_optional_form("algorithm", 32),
                ssim=ssim_value,
                ber=round(ber_value, 6),
                delivery_uuid=_optional_form("delivery_uuid", 36),
                fingerprint_id=_optional_form("fingerprint_id", 32),
                host_type=_optional_form("host_type", 16),
                original_hash=hashlib.sha256(ori_b64.encode()).hexdigest(),
                extracted_hash=hashlib.sha256(ext_b64.encode()).hexdigest(),
                verified_by=identity.get("number", "unknown"),
                verified_at=datetime.now(UTC),
                ip_address=request.remote_addr,
            )
            db.session.add(verification)
            db.session.commit()

            log_action(
                identity.get("number", "unknown"),
                identity.get("username", "unknown"),
                "水印比对",
                "成功",
                f"nc_value={round(nc_value, 6)}",
            )

            return {
                "status": True,
                "nc_value": round(nc_value, 6),
                "original_watermark": ori_b64,
                "extracted_watermark": ext_b64,
            }, 200
        except Exception as e:
            logging.error(str(e))
            return {"status": False, "msg": "操作失败，请稍后重试"}, 500


class GetOriginalWatermarkResource(Resource):
    @jwt_required()
    def post(self):
        data = request.get_json() or {}
        app_id = data.get("number")
        item = db.session.get(Application, app_id)
        if not item:
            return {"status": False, "msg": "未找到对应水印"}, 404
        denial = ensure_owner_or_admin(item)
        if denial:
            return denial
        if not item.qrcode:
            return {"status": False, "msg": "未找到对应水印"}, 404
        return {"status": True, "original_watermark": item.qrcode}, 200


class WatermarkVerificationRecordsResource(Resource):
    """List watermark verification records with pagination.
    Supports ?data_type=vector|raster filter, ?sort=nc_value query and an
    optional ?from / ?to ISO-date (or ISO-datetime) verified_at window."""

    @admin_required
    def get(self):
        page = request.args.get("page", 1, type=int)
        page_size = min(request.args.get("pageSize", 20, type=int), 100)
        data_type = request.args.get("data_type", "").strip().lower()
        sort_by = request.args.get("sort", "verified_at")

        raw_from = request.args.get("from")
        raw_to = request.args.get("to")
        from_dt = _parse_iso_dt(raw_from) if raw_from else None
        to_dt = _parse_iso_dt(raw_to) if raw_to else None
        if (raw_from and from_dt is None) or (raw_to and to_dt is None):
            return {"status": False, "msg": "时间格式错误，应为 ISO 日期（如 2026-01-01）"}, 400

        query = WatermarkVerification.query
        if data_type in ("vector", "raster"):
            query = query.filter(WatermarkVerification.data_type == data_type)
        if from_dt is not None:
            query = query.filter(WatermarkVerification.verified_at >= from_dt)
        if to_dt is not None:
            # A bare date ("to=2026-02-01") includes the whole day; an explicit
            # datetime is an exact inclusive bound.
            if ":" in raw_to:
                query = query.filter(WatermarkVerification.verified_at <= to_dt)
            else:
                query = query.filter(WatermarkVerification.verified_at < to_dt + timedelta(days=1))
        if sort_by == "nc_value":
            query = query.order_by(WatermarkVerification.nc_value.desc())
        else:
            query = query.order_by(WatermarkVerification.verified_at.desc())

        pagination = query.paginate(page=page, per_page=page_size, error_out=False)

        records = []
        for r in pagination.items:
            records.append(r.to_dict())

        return {
            "status": True,
            "data": records,
            "pages": {"total": pagination.total, "page": page, "page_size": page_size},
        }, 200


class WatermarkVerificationStatsResource(Resource):
    """GET /api/watermark/verification_stats — admin, server-side aggregation
    for the watermark quality page (stats cards that must not be computed from
    the current page of 20 records).

    All aggregates run as SQL (count/avg/min/max, group_by, case); the median
    is fetched through a two-row OFFSET window instead of pulling the column.

    ``days`` (default 30, clamped to 1..365) sets the length of the ``daily``
    series only — the other stats cover the full history, so an old deployment
    still gets meaningful totals. Optional ``data_type=vector|raster`` filters
    every stat.
    """

    @admin_required
    def get(self):
        days = request.args.get("days", 30, type=int)
        if days is None:
            days = 30
        days = max(1, min(days, 365))
        data_type = request.args.get("data_type", "").strip().lower()

        base = WatermarkVerification.query
        if data_type in ("vector", "raster"):
            base = base.filter(WatermarkVerification.data_type == data_type)

        # --- one aggregate row: count/avg/min/max + covered time range ---
        overall = base.with_entities(
            func.count(WatermarkVerification.id),
            func.avg(WatermarkVerification.nc_value),
            func.min(WatermarkVerification.nc_value),
            func.max(WatermarkVerification.nc_value),
            func.min(WatermarkVerification.verified_at),
            func.max(WatermarkVerification.verified_at),
        ).one()
        total = int(overall[0] or 0)

        # --- median via a bounded OFFSET window (no full column pull) ---
        p50_nc = None
        if total:
            k = (total - 1) // 2
            middle = (
                base.with_entities(WatermarkVerification.nc_value)
                .order_by(WatermarkVerification.nc_value.asc())
                .offset(k)
                .limit(2)
                .all()
            )
            values = [float(row[0]) for row in middle]
            if values:
                p50_nc = values[0] if total % 2 == 1 else sum(values) / len(values)

        # --- grouped breakdowns ---
        by_data_type = [
            {
                "data_type": row[0] or "unknown",
                "count": int(row[1]),
                "avg_nc": round(float(row[2]), 6) if row[2] is not None else None,
            }
            for row in base.with_entities(
                WatermarkVerification.data_type,
                func.count(),
                func.avg(WatermarkVerification.nc_value),
            )
            .group_by(WatermarkVerification.data_type)
            .order_by(func.count().desc())
            .all()
        ]

        algo_col = func.coalesce(WatermarkVerification.algorithm, "unknown")
        by_algorithm = [
            {
                "algorithm": row[0],
                "count": int(row[1]),
                "avg_nc": round(float(row[2]), 6) if row[2] is not None else None,
                "avg_ber": round(float(row[3]), 6) if row[3] is not None else None,
            }
            for row in base.with_entities(
                algo_col,
                func.count(),
                func.avg(WatermarkVerification.nc_value),
                func.avg(WatermarkVerification.ber),
            )
            .group_by(algo_col)
            .order_by(func.count().desc(), algo_col.asc())
            .all()
        ]

        # --- NC histogram, bucketed server-side ---
        bucket = case(
            (WatermarkVerification.nc_value < 0.1, 0),
            (WatermarkVerification.nc_value < 0.2, 1),
            (WatermarkVerification.nc_value < 0.3, 2),
            (WatermarkVerification.nc_value < 0.4, 3),
            (WatermarkVerification.nc_value < 0.5, 4),
            (WatermarkVerification.nc_value < 0.6, 5),
            (WatermarkVerification.nc_value < 0.7, 6),
            (WatermarkVerification.nc_value < 0.8, 7),
            (WatermarkVerification.nc_value < 0.9, 8),
            else_=9,
        )
        hist_rows = dict(base.with_entities(bucket, func.count()).group_by(bucket).all())
        nc_histogram = [
            {"bucket": f"{i / 10:.1f}-{(i + 1) / 10:.1f}", "count": int(hist_rows.get(i, 0))} for i in range(10)
        ]

        # --- daily series over the last N days (func.date works on MySQL+SQLite) ---
        now = datetime.now(UTC)
        day_expr = func.date(WatermarkVerification.verified_at)
        day_start = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
        daily_rows = {
            str(row[0]): (int(row[1]), row[2])
            for row in base.with_entities(
                day_expr,
                func.count(),
                func.avg(WatermarkVerification.nc_value),
            )
            .filter(WatermarkVerification.verified_at >= day_start)
            .group_by(day_expr)
            .all()
        }
        daily = []
        for i in range(days - 1, -1, -1):
            day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            count, avg = daily_rows.get(day, (0, None))
            daily.append({"date": day, "count": count, "avg_nc": round(float(avg), 6) if avg is not None else None})

        low_nc_count = base.filter(WatermarkVerification.nc_value < 0.8).count()

        def _round(value):
            return round(float(value), 6) if value is not None else None

        return {
            "status": True,
            "stats": {
                "total": total,
                "avg_nc": _round(overall[1]),
                "min_nc": _round(overall[2]),
                "max_nc": _round(overall[3]),
                "p50_nc": _round(p50_nc),
                "low_nc_count": int(low_nc_count),
                "by_data_type": by_data_type,
                "by_algorithm": by_algorithm,
                "nc_histogram": nc_histogram,
                "daily": daily,
                "range": {
                    "min_verified_at": overall[4].isoformat() if overall[4] is not None else None,
                    "max_verified_at": overall[5].isoformat() if overall[5] is not None else None,
                },
            },
        }, 200


class WatermarkPreviewResource(Resource):
    """Preview watermark capacity and expected distortion without embedding."""

    @jwt_required()
    def post(self):
        data = request.get_json() or {}
        app_id = data.get("application_id")
        if not app_id:
            return {"status": False, "msg": "缺少申请编号"}, 400

        item = db.session.get(Application, app_id)
        if not item:
            return {"status": False, "msg": "申请不存在"}, 404

        data_type = (item.data_type or "vector").lower()

        try:
            if data_type == "raster":
                return self._preview_raster(item, data)
            else:
                return self._preview_vector(item, data)
        except Exception as e:
            logging.error(str(e))
            return {"status": False, "msg": "预览失败"}, 500

    def _preview_vector(self, item, data):
        import geopandas as gpd

        from algorithm.get_coor import get_coor_nested
        from algorithm.quality_metrics import capacity_report

        shp_record = db.session.get(Shp, item.data_id)
        if not shp_record or not shp_record.shp_file_path:
            return {"status": False, "msg": "未找到矢量数据"}, 404

        shp_file = shp_record.shp_file_path
        if not os.path.exists(shp_file):
            candidate = os.path.join(current_app.root_path, shp_file.lstrip("/\\"))
            if os.path.exists(candidate):
                shp_file = candidate
            else:
                return {"status": False, "msg": "数据文件丢失"}, 404

        n = data.get("n", 4)
        side_length = data.get("side_length", 45)

        shpfile = gpd.read_file(shp_file)
        coor_nested, feature_type = get_coor_nested(shpfile)

        # Count total vertices
        total_vertices = 0
        for i in range(coor_nested.shape[1]):
            arr = coor_nested[:, i][0]
            if isinstance(arr, np.ndarray):
                if arr.ndim == 1:
                    total_vertices += arr.size
                else:
                    total_vertices += sum(a.size for a in arr)
            else:
                total_vertices += 1

        # Calculate watermark bit count
        n_bits_needed = side_length**2 - 192  # minus detection patterns
        cap = capacity_report(total_vertices, n_bits_needed, n)

        return {
            "status": True,
            "data_type": "vector",
            "preview": {
                "total_vertices": total_vertices,
                "watermark_bits": n_bits_needed,
                "capacity": cap,
                "params": {"n": n, "side_length": side_length},
                "estimated_utilization": cap["utilization_percent"],
            },
        }, 200

    def _preview_raster(self, item, data):
        from algorithm.quality_metrics import capacity_report

        raster_record = db.session.get(RasterData, item.data_id)
        if not raster_record or not raster_record.raster_file_path:
            return {"status": False, "msg": "未找到栅格数据"}, 404

        host_path = raster_record.raster_file_path
        if not os.path.exists(host_path):
            candidate = os.path.join(current_app.root_path, host_path.lstrip("/\\"))
            if os.path.exists(candidate):
                host_path = candidate
            else:
                return {"status": False, "msg": "数据文件丢失"}, 404

        host_img = Image.open(host_path)
        w, h = host_img.size
        total_pixels = w * h

        min_wm = data.get("min_wm_size", 64)
        max_wm = data.get("max_wm_size", 512)
        wm_w = max(min_wm, min(max_wm, w))
        wm_h = max(min_wm, min(max_wm, h))
        bit_count = wm_w * wm_h

        cap = capacity_report(total_pixels, bit_count, n=1)

        return {
            "status": True,
            "data_type": "raster",
            "preview": {
                "host_size": {"width": w, "height": h},
                "total_pixels": total_pixels,
                "watermark_size": {"width": wm_w, "height": wm_h},
                "watermark_bits": bit_count,
                "capacity": cap,
                "estimated_utilization": cap["utilization_percent"],
            },
        }, 200


class BatchGenerateWatermarkResource(Resource):
    """
    批量生成水印二维码
    ---
    tags: [Watermark]
    security: [Bearer: []]
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [application_ids]
          properties:
            application_ids:
              type: array
              items: {type: integer}
              description: 申请编号列表
            purpose: {type: string, description: 用途}
            usage_scope: {type: string, description: 使用范围}
            security_level: {type: string, description: 安全级别}
            custom_tag: {type: string, description: 自定义标签}
            reason: {type: string, description: 原因}
    responses:
      200: {description: 批量水印生成完成}
      400: {description: 参数错误}
    """

    @admin_role_required("admin1")
    def post(self):
        data = request.get_json() or {}
        app_ids = data.get("application_ids")

        if not app_ids or not isinstance(app_ids, list):
            return {"status": False, "msg": "缺少 application_ids 列表"}, 400

        results = []
        success_count = 0
        fail_count = 0

        # One IN query for the whole batch; missing ids keep the same
        # "申请不存在" per-item result as the former session.get loop.
        preload_ids = [value for value in app_ids if isinstance(value, int)]
        app_map = _preload_applications(preload_ids)
        # The preloaded rows must survive the per-item commits: with the
        # default expire_on_commit each commit would expire them and the next
        # iteration would reload one row anyway (the IN query would save
        # nothing). Rollback still expires the failed row, so error handling
        # keeps seeing database state. Restored before returning.
        session_impl = db.session()
        previous_expire_on_commit = session_impl.expire_on_commit
        session_impl.expire_on_commit = False

        for app_id in app_ids:
            try:
                # Normal integer ids come from the batched map; anything else
                # keeps the original per-item lookup semantics.
                item = app_map.get(app_id) if isinstance(app_id, int) else db.session.get(Application, app_id)
                if not item:
                    results.append({"id": app_id, "success": False, "error": "申请不存在"})
                    fail_count += 1
                    continue

                # Build QR content with signature
                qr_content, signature = build_qr_text(item, data)

                # Auto-detect QR version based on content length
                qr_version = get_qr_version(len(qr_content))

                # Generate QR code
                qr = qrcode.QRCode(
                    version=qr_version,
                    error_correction=qrcode.constants.ERROR_CORRECT_M,
                    box_size=10,
                    border=4,
                )
                qr.add_data(qr_content)
                qr.make(fit=True)

                img = qr.make_image(fill_color="black", back_color="white")

                # Convert to base64
                buffered = io.BytesIO()
                img.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()

                # Save all metadata to database
                item.qrcode = img_str
                item.qr_text = qr_content
                item.watermark_generated = True
                item.qr_version = qr_version
                item.qr_signature = signature
                item.generation_timestamp = datetime.now(UTC)

                # Save optional fields
                for field in ["purpose", "usage_scope", "security_level", "custom_tag"]:
                    if data.get(field):
                        setattr(item, field, str(data.get(field)).strip())

                if data.get("reason"):
                    item.reason = str(data.get("reason")).strip()

                db.session.commit()

                log_action(
                    item.applicant_user_number,
                    item.applicant_name,
                    "批量水印生成",
                    "成功",
                    f"app_id={item.id} data_alias={item.data_alias} qr_version={qr_version}",
                )
                record_watermark(data_type=item.data_type or "vector")

                results.append({"id": app_id, "success": True, "qr_version": qr_version})
                success_count += 1

            except Exception as e:
                logging.error(f"Batch generate watermark failed for app_id={app_id}: {e}")
                db.session.rollback()
                results.append({"id": app_id, "success": False, "error": str(e)})
                fail_count += 1

        session_impl.expire_on_commit = previous_expire_on_commit
        return {
            "status": True,
            "results": results,
            "summary": {"total": len(app_ids), "success": success_count, "failed": fail_count},
        }, 200


class BatchEmbedWatermarkResource(Resource):
    """
    批量嵌入水印到数据文件
    ---
    tags: [Watermark]
    security: [Bearer: []]
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [application_ids]
          properties:
            application_ids:
              type: array
              items: {type: integer}
              description: 申请编号列表
    responses:
      200: {description: 批量水印嵌入完成}
      400: {description: 参数错误}
    """

    @admin_role_required("admin2")
    def post(self):
        data = request.get_json() or {}
        app_ids = data.get("application_ids")

        if not app_ids or not isinstance(app_ids, list):
            return {"status": False, "msg": "缺少 application_ids 列表"}, 400

        results = []
        success_count = 0
        fail_count = 0

        # One IN query for the whole batch; missing ids keep the same
        # "申请不存在" per-item result as the former session.get loop.
        preload_ids = [value for value in app_ids if isinstance(value, int)]
        app_map = _preload_applications(preload_ids)
        # The preloaded rows must survive the per-item commits: with the
        # default expire_on_commit each commit would expire them and the next
        # iteration would reload one row anyway (the IN query would save
        # nothing). Rollback still expires the failed row, so error handling
        # keeps seeing database state. Restored before returning.
        session_impl = db.session()
        previous_expire_on_commit = session_impl.expire_on_commit
        session_impl.expire_on_commit = False

        for app_id in app_ids:
            try:
                # Normal integer ids come from the batched map; anything else
                # keeps the original per-item lookup semantics.
                item = app_map.get(app_id) if isinstance(app_id, int) else db.session.get(Application, app_id)
                if not item:
                    results.append({"id": app_id, "success": False, "error": "申请不存在"})
                    fail_count += 1
                    continue

                if not item.qrcode:
                    results.append({"id": app_id, "success": False, "error": "水印尚未生成"})
                    fail_count += 1
                    continue

                data_type = (item.data_type or "vector").lower()

                if data_type == "raster":
                    self._embed_raster(item)
                else:
                    self._embed_vector(item)

                results.append({"id": app_id, "success": True, "data_type": data_type})
                success_count += 1

            except Exception as e:
                logging.error(f"Batch embed watermark failed for app_id={app_id}: {e}")
                db.session.rollback()
                results.append({"id": app_id, "success": False, "error": str(e)})
                fail_count += 1

        session_impl.expire_on_commit = previous_expire_on_commit
        return {
            "status": True,
            "results": results,
            "summary": {"total": len(app_ids), "success": success_count, "failed": fail_count},
        }, 200

    def _embed_vector(self, item):
        shp_record = db.session.get(Shp, item.data_id)
        if not shp_record or not shp_record.shp_file_path:
            raise ValueError(f"未找到编号为 {item.data_id} 的矢量数据文件")

        shp_file = shp_record.shp_file_path
        if not os.path.exists(shp_file):
            candidate = os.path.join(current_app.root_path, shp_file.lstrip("/\\"))
            if os.path.exists(candidate):
                shp_file = candidate
            else:
                raise ValueError("数据文件在服务器上丢失")

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
            "批量矢量水印嵌入",
            "成功",
            f"app_id={item.id} data_id={item.data_id} vertices={cap.get('total_vertices', 'N/A')} utilization={cap.get('utilization_percent', 'N/A')}%",
        )

    def _embed_raster(self, item):
        raster_record = db.session.get(RasterData, item.data_id)
        if not raster_record or not raster_record.raster_file_path:
            raise ValueError(f"未找到编号为 {item.data_id} 的栅格数据文件")

        host_path = raster_record.raster_file_path
        if not os.path.exists(host_path):
            candidate = os.path.join(current_app.root_path, host_path.lstrip("/\\"))
            if os.path.exists(candidate):
                host_path = candidate
            else:
                raise ValueError("数据文件在服务器上丢失")

        qr_img = Image.open(io.BytesIO(base64.b64decode(item.qrcode))).convert("L")
        out_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "crmark", f"app_{item.id}")
        os.makedirs(out_dir, exist_ok=True)
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
            "批量栅格水印嵌入",
            "成功",
            f"app_id={item.id} data_id={item.data_id} bit_count={result.get('bit_count', 'N/A')} changed={result.get('changed_count', 'N/A')}{psnr_str}",
        )
