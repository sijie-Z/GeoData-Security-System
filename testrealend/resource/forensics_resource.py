"""v3 forensics endpoints (contract locked with the UI line, taskbook round B §1).

  POST /api/forensics/verify              multipart file | JSON {qr_text}
  POST /api/forensics/trace               same inputs (+ optional application_id) + provenance
  GET  /api/forensics/deliveries          ?application_id=  (admin or owner)
  GET  /api/forensics/deliveries/<uuid>   (admin or owner)
  POST /api/forensics/anchor/build        (admin)
  GET  /api/forensics/keyinfo             (admin)

Verify/trace detect fingerprints either from raw QR text or from an uploaded
artifact (zip/shp/tif/png): every READY delivery of the matching type is tried
as an extraction candidate (newest first, max 50). Verify responses NEVER carry
PII; provenance is trace-only.
"""

import hashlib
import hmac
import json
import logging
import os
import shutil
import tempfile
import zipfile
from datetime import UTC, datetime

from cryptography.hazmat.primitives import serialization
from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource

from algorithm.extract import extract as vector_extract
from algorithm.raster_dwt_watermark import extract_dwt
from algorithm.raster_histogram_watermark import extract_histogram
from algorithm.raster_reversible_watermark import decode_reversible
from crypto.keys import ensure_active_key
from crypto.keys import keyinfo as crypto_keyinfo
from crypto.payload import is_v2_text, parse_qr_text
from delivery.artifact import file_root, shp_component_root
from evidence.anchor import build_batch
from evidence.chain import get_events, verify_stream
from extension.extension import db, limiter
from model.Application import Application
from model.anchor_record import AnchorRecord
from model.Download_Record import DownloadRecord
from model.download_delivery import DownloadDelivery
from resource.watermark_utils import QR_SECRET_KEY, decode_qr_from_image
from resource.watermark_utils import parse_qr_text as parse_v1_lines
from utils.required import admin_required

V1_BANNER = "=== SPATIAL DATA TRACKING SYSTEM ==="
CANDIDATE_LIMIT = 50
ZIP_MAX_MEMBERS = 50
ZIP_MAX_TOTAL_BYTES = 300 * 1024 * 1024
RASTER_IMAGE_EXTS = (".tif", ".tiff", ".png", ".jpg", ".jpeg")


# --------------------------------------------------------------------------- #
# helpers                                                                      #
# --------------------------------------------------------------------------- #


def _unzip_safe(zip_path, extract_dir):
    """Bomb-proof extraction: <=50 members, <=300MB total, no absolute paths / '..'."""
    with zipfile.ZipFile(zip_path) as zf:
        infos = zf.infolist()
        if len(infos) > ZIP_MAX_MEMBERS:
            raise ValueError(f"压缩包成员数超过 {ZIP_MAX_MEMBERS}，拒绝解压")
        total = 0
        for info in infos:
            norm = info.filename.replace("\\", "/")
            parts = [p for p in norm.split("/") if p not in ("", ".")]
            if norm.startswith("/") or (len(norm) > 1 and norm[1] == ":") or ".." in parts:
                raise ValueError(f"非法文件路径: {info.filename}")
            total += info.file_size
        if total > ZIP_MAX_TOTAL_BYTES:
            raise ValueError("解压总量超过 300MB，拒绝解压")
        real_root = os.path.realpath(extract_dir)
        for info in infos:
            target = os.path.realpath(os.path.join(extract_dir, info.filename.replace("\\", "/")))
            if not (target == real_root or target.startswith(real_root + os.sep)):
                raise ValueError(f"非法文件路径: {info.filename}")
        os.makedirs(extract_dir, exist_ok=True)
        zf.extractall(extract_dir)


def _find_vector_base(directory):
    for root, _dirs, files in os.walk(directory):
        for name in sorted(files):
            if not name.lower().endswith(".shp"):
                continue
            base = os.path.join(root, name)
            stem = os.path.splitext(base)[0]
            if os.path.exists(f"{stem}.shx") and os.path.exists(f"{stem}.dbf"):
                return base
    return None


def _find_image(directory):
    for root, _dirs, files in os.walk(directory):
        for name in sorted(files):
            if name.lower().endswith(RASTER_IMAGE_EXTS):
                return os.path.join(root, name)
    return None


def _verify_v1_hmac(text):
    """v1 HMAC convention (same as the extract resources): signer covers every
    line before the ``Signature:`` line — including the banner — and only the
    first 16 hex chars are compared."""
    lines = text.split("\n")
    sig_idx = next((i for i, line in enumerate(lines) if line.startswith("Signature:")), None)
    if sig_idx is None:
        return False
    content_to_verify = "\n".join(lines[:sig_idx])
    claimed = lines[sig_idx].partition(":")[2].strip()
    expected = hmac.new(QR_SECRET_KEY.encode(), content_to_verify.encode(), hashlib.sha256).hexdigest()[:16]
    return hmac.compare_digest(claimed, expected)


def _parse_vr_data(raw):
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except Exception:
        return None
    return data if isinstance(data, dict) and data.get("vr") else None


def _as_utc(dt):
    if dt is None:
        return None
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def _chain_summary(stream_id):
    try:
        summary = verify_stream(stream_id)
        return {"valid": bool(summary["valid"]), "length": int(summary["length"])}
    except Exception:
        logging.warning("chain verify failed for stream %s", stream_id, exc_info=True)
        return {"valid": False, "length": 0}


def _chain_full(stream_id):
    try:
        summary = verify_stream(stream_id)
        return {"valid": bool(summary["valid"]), "length": int(summary["length"]), "broken_at": summary["broken_at"]}
    except Exception:
        logging.warning("chain verify failed for stream %s", stream_id, exc_info=True)
        return {"valid": False, "length": 0, "broken_at": None}


def _anchor_for(delivery):
    """Latest AnchorRecord covering this delivery (created after ready_at), else None."""
    if delivery.ready_at is None:
        return None
    ready = _as_utc(delivery.ready_at)
    records = AnchorRecord.query.order_by(AnchorRecord.created_at.desc(), AnchorRecord.id.desc()).all()
    for record in records:
        if _as_utc(record.created_at) >= ready:
            return record
    return None


# --------------------------------------------------------------------------- #
# detection (shared by verify / trace)                                         #
# --------------------------------------------------------------------------- #


def _detect_qr_text(text):
    """Detect from raw QR text: v2 (verified + delivery lookup) / v1 / none / tamper."""
    if is_v2_text(text):
        try:
            parsed = parse_qr_text(text)
        except Exception as e:
            return {"kind": "tamper", "error": str(e)}
        delivery = (
            DownloadDelivery.query.filter_by(fingerprint_id=parsed["fid_hex"])
            .order_by(DownloadDelivery.delivery_id.desc())
            .first()
        )
        if delivery is None:
            by_id = db.session.get(DownloadDelivery, parsed["delivery"])
            if by_id is not None and by_id.fingerprint_id == parsed["fid_hex"]:
                delivery = by_id
        if delivery is None:
            return {"kind": "v2unknown", "parsed": parsed}
        return {"kind": "v2", "delivery": delivery, "parsed": parsed}
    if V1_BANNER in text:
        return {"kind": "v1", "qr_text": text, "signature_ok": _verify_v1_hmac(text)}
    return {"kind": "none"}


def _detect_vector_shp(shp_path, work_root):
    """Try every READY vector delivery (newest first) as an extraction candidate."""
    candidates = (
        DownloadDelivery.query.filter_by(data_type="vector", status="READY")
        .order_by(DownloadDelivery.delivery_id.desc())
        .limit(CANDIDATE_LIMIT)
        .all()
    )
    for delivery in candidates:
        vr_data = _parse_vr_data(delivery.vr_data)
        if vr_data is None:
            continue
        out_dir = tempfile.mkdtemp(prefix="fx_vec_", dir=work_root)
        try:
            _shp_out, wm_png = vector_extract(
                shp_path, vr_data["vr"], side_length=vr_data.get("side_length") or 45, output_dir=out_dir
            )
        except Exception as e:
            logging.info("forensics: vector candidate %s skipped (%s)", delivery.uuid, e)
            continue
        text = decode_qr_from_image(wm_png)
        if not text:
            continue
        if is_v2_text(text):
            try:
                parsed = parse_qr_text(text)
            except Exception as e:
                return {"kind": "tamper", "error": str(e)}
            if parsed["fid_hex"] == delivery.fingerprint_id:
                return {"kind": "v2", "delivery": delivery, "parsed": parsed, "fid_confidence": "候选交付提取一致"}
        elif V1_BANNER in text:
            return {"kind": "v1", "qr_text": text, "signature_ok": _verify_v1_hmac(text)}
    return None


def _detect_raster_stego(image_path, work_root):
    """Try every READY raster delivery whose meta file is on disk, newest first."""
    candidates = (
        DownloadDelivery.query.filter_by(data_type="raster", status="READY")
        .order_by(DownloadDelivery.delivery_id.desc())
        .limit(CANDIDATE_LIMIT)
        .all()
    )
    for delivery in candidates:
        meta_path = delivery.artifact_meta_path
        if not meta_path or not os.path.isfile(meta_path):
            continue
        out_png = os.path.join(tempfile.mkdtemp(prefix="fx_ras_", dir=work_root), "wm.png")
        decoder = {"dwt": extract_dwt, "histogram": extract_histogram}.get(delivery.algorithm or "", decode_reversible)
        try:
            decoder(image_path, meta_path, out_png)
        except Exception as e:
            logging.info("forensics: raster candidate %s skipped (%s)", delivery.uuid, e)
            continue
        text = decode_qr_from_image(out_png)
        if not text:
            continue
        if is_v2_text(text):
            try:
                parsed = parse_qr_text(text)
            except Exception as e:
                return {"kind": "tamper", "error": str(e)}
            if parsed["fid_hex"] == delivery.fingerprint_id:
                return {"kind": "v2", "delivery": delivery, "parsed": parsed, "fid_confidence": "候选交付提取一致"}
        elif V1_BANNER in text:
            return {"kind": "v1", "qr_text": text, "signature_ok": _verify_v1_hmac(text)}
    return None


def _detect_upload(saved_path, work_root):
    """Detect from an uploaded file (zip / shp / raster image / plain QR image)."""
    low = saved_path.lower()
    vector_shp = None
    image_path = None
    if low.endswith(".zip"):
        extract_dir = os.path.join(work_root, "unzipped")
        try:
            _unzip_safe(saved_path, extract_dir)
        except Exception as e:
            return {"kind": "error", "msg": f"压缩包处理失败: {e}"}
        vector_shp = _find_vector_base(extract_dir)
        image_path = _find_image(extract_dir)
    elif low.endswith(".shp"):
        vector_shp = saved_path
    elif low.endswith(RASTER_IMAGE_EXTS):
        image_path = saved_path
    else:
        return {"kind": "none"}

    detection = {"kind": "none"}
    if vector_shp:
        found = _detect_vector_shp(vector_shp, work_root)
        if found:
            found["artifact_check"] = ("vector", vector_shp)
            found["vector_path"] = vector_shp
            return found
    if image_path:
        found = _detect_raster_stego(image_path, work_root)
        if found:
            found["artifact_check"] = ("raster", image_path)
            found["image_path"] = image_path
            return found
        text = decode_qr_from_image(image_path)
        if text:
            found = _detect_qr_text(text)
            if found["kind"] in ("v2", "v2unknown", "tamper", "v1"):
                found["artifact_check"] = None
                return found
    if vector_shp:
        detection["vector_path"] = vector_shp
    if image_path:
        detection["image_path"] = image_path
    return detection


def _run_detection():
    """Shared entry: multipart file or JSON {qr_text}. Returns (detection, tmp_dir)."""
    if "file" in request.files and request.files["file"].filename:
        tmp_dir = tempfile.mkdtemp(prefix="forensics_")
        uploaded = request.files["file"]
        name = os.path.basename(uploaded.filename) or "upload.bin"
        path = os.path.join(tmp_dir, name)
        try:
            uploaded.save(path)
            return _detect_upload(path, tmp_dir), tmp_dir
        except Exception:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            raise
    data = request.get_json(silent=True) or {}
    text = (data.get("qr_text") or "").strip()
    if text:
        return _detect_qr_text(text), None
    return {"kind": "empty"}, None


# --------------------------------------------------------------------------- #
# response assembly                                                            #
# --------------------------------------------------------------------------- #


def _empty_fields():
    return {
        "fid": None,
        "fid_short": None,
        "delivery_uuid": None,
        "data_alias": None,
        "data_type": None,
        "issued_at": None,
        "signature_valid": False,
        "artifact_root": None,
        "artifact_root_match": None,
        "chain": {"valid": True, "length": 0},
    }


def _v2_fields(detection):
    delivery = detection["delivery"]
    app_row = db.session.get(Application, delivery.application_id)
    artifact_match = None
    artifact_check = detection.get("artifact_check")
    if artifact_check:
        try:
            kind, path = artifact_check
            root = shp_component_root(path) if kind == "vector" else file_root(path)
            artifact_match = root == delivery.artifact_root
        except Exception as e:
            logging.warning("artifact root comparison failed: %s", e)
            artifact_match = False
    msg = "验证通过：指纹与交付记录一致"
    if artifact_check is not None:
        msg += "，产物根一致" if artifact_match else f"，但产物根不一致（artifact_root_match=false）"
    return {
        "found": True,
        "watermark_version": 2,
        "fid": delivery.fingerprint_id,
        "fid_short": delivery.fingerprint_id[:12],
        "delivery_uuid": delivery.uuid,
        "data_alias": app_row.data_alias if app_row else None,
        "data_type": delivery.data_type,
        "issued_at": delivery.created_at.isoformat() if delivery.created_at else None,
        "signature_valid": True,
        "artifact_root": delivery.artifact_root,
        "artifact_root_match": artifact_match,
        "chain": _chain_summary(delivery.uuid),
        "msg": msg,
    }


def _verify_view(detection):
    kind = detection.get("kind")
    if kind == "v2":
        return _v2_fields(detection)
    fields = _empty_fields()
    if kind == "v2unknown":
        parsed = detection["parsed"]
        fields.update(
            {
                "watermark_version": 2,
                "fid": parsed["fid_hex"],
                "fid_short": parsed["fid_hex"][:12],
                "signature_valid": True,
                "msg": "载荷签名有效，但数据库中未找到对应交付记录（数据库可能已重建）",
            }
        )
        return fields
    if kind == "tamper":
        fields.update(
            {
                "watermark_version": 2,
                "signature_valid": False,
                "chain": {"valid": False, "length": 0},
                "msg": "签名验证失败，载荷可能被篡改",
            }
        )
        return fields
    if kind == "v1":
        ok = bool(detection.get("signature_ok"))
        fields.update(
            {
                "watermark_version": 1,
                "signature_valid": ok,
                "found": ok,
                "msg": "检测到 v1 版水印，请用解码平台按申请编号查询完整溯源信息"
                if ok
                else "检测到 v1 版水印，但签名校验失败",
            }
        )
        return fields
    fields["msg"] = "未检测到本系统的交付指纹（可能为原件、旧版水印或非本系统文件）"
    return fields


def _build_provenance(app_row):
    approvals = []
    for stage, name_field, number_field, time_field, comment_field in (
        ("adm1", "adm1_name", "adm1_user_number", "adm1_approval_time", "adm1_comment"),
        ("adm2", "adm2_name", "adm2_user_number", "adm2_approval_time", "adm2_comment"),
    ):
        name = getattr(app_row, name_field, None)
        number = getattr(app_row, number_field, None)
        if name is None and number is None:
            continue
        approval_time = getattr(app_row, time_field, None)
        approvals.append(
            {
                "stage": stage,
                "name": name,
                "time": approval_time.isoformat() if approval_time else None,
                "comment": getattr(app_row, comment_field, None),
            }
        )

    downloads = []
    for record in DownloadRecord.query.filter_by(application_id=app_row.id).all():
        delivery_uuid = None
        if record.delivery_id is not None:
            delivery = db.session.get(DownloadDelivery, record.delivery_id)
            delivery_uuid = delivery.uuid if delivery else None
        downloads.append(
            {
                "user_number": record.download_user_number,
                "time": record.download_time.isoformat() if record.download_time else None,
                "ip": record.download_ip,
                "delivery_uuid": delivery_uuid,
            }
        )

    return {
        "applicant_name": app_row.applicant_name,
        "applicant_number": app_row.applicant_user_number,
        "application_id": app_row.id,
        "data_name": app_row.data_name,
        "approvals": approvals,
        "downloads": downloads,
    }


def _trace_v1_by_application(application_id, detection, work_root):
    """Optional v1 trace: extract with the application's stored vr_data and parse the banner text."""
    app_row = db.session.get(Application, application_id)
    if app_row is None:
        return None
    vr_data = _parse_vr_data(app_row.vr_data)
    vector_path = detection.get("vector_path")
    if vr_data is None or not vector_path:
        return None
    out_dir = tempfile.mkdtemp(prefix="fx_v1_", dir=work_root)
    try:
        _shp, wm_png = vector_extract(
            vector_path, vr_data["vr"], side_length=vr_data.get("side_length") or 45, output_dir=out_dir
        )
    except Exception as e:
        logging.info("forensics: v1 trace extraction failed (%s)", e)
        return None
    text = decode_qr_from_image(wm_png)
    if not text or V1_BANNER not in text:
        return None
    ok = _verify_v1_hmac(text)
    parsed = parse_v1_lines(text)
    app_id_in_text = parsed.get("AppID")
    fields = _empty_fields()
    fields.update(
        {
            "found": ok,
            "watermark_version": 1,
            "signature_valid": ok,
            "msg": f"v1 水印解析成功（载荷 AppID={app_id_in_text}，签名{'通过' if ok else '失败'}）",
            "provenance": _build_provenance(app_row),
        }
    )
    return fields


# --------------------------------------------------------------------------- #
# resources                                                                    #
# --------------------------------------------------------------------------- #


class ForensicsVerifyResource(Resource):
    """POST /api/forensics/verify — admin only, never contains PII."""

    @admin_required
    @limiter.limit("60 per minute")
    def post(self):
        detection, tmp_dir = _run_detection()
        try:
            if detection["kind"] == "error":
                return {"status": False, "msg": detection["msg"]}, 400
            if detection["kind"] == "empty":
                return {"status": False, "msg": "请提供文件或 qr_text"}, 400
            return {"status": True, **_verify_view(detection)}, 200
        finally:
            if tmp_dir:
                shutil.rmtree(tmp_dir, ignore_errors=True)


class ForensicsTraceResource(Resource):
    """POST /api/forensics/trace — admin only, verify fields + provenance (with PII)."""

    @admin_required
    @limiter.limit("60 per minute")
    def post(self):
        detection, tmp_dir = _run_detection()
        try:
            if detection["kind"] == "error":
                return {"status": False, "msg": detection["msg"]}, 400
            if detection["kind"] == "empty":
                return {"status": False, "msg": "请提供文件或 qr_text"}, 400

            view = _verify_view(detection)
            view["provenance"] = None
            if detection["kind"] == "v2":
                app_row = db.session.get(Application, detection["delivery"].application_id)
                if app_row is not None:
                    view["provenance"] = _build_provenance(app_row)
            else:
                application_id = request.form.get("application_id", type=int)
                if application_id is None:
                    data = request.get_json(silent=True) or {}
                    try:
                        application_id = int(data.get("application_id")) if data.get("application_id") else None
                    except (TypeError, ValueError):
                        application_id = None
                if application_id is not None and tmp_dir:
                    v1_view = _trace_v1_by_application(application_id, detection, tmp_dir)
                    if v1_view is not None:
                        view = v1_view
                    elif detection["kind"] == "v1":
                        # v1 text recognised but no vr_data extraction possible: use the app row directly
                        app_row = db.session.get(Application, application_id)
                        if app_row is not None:
                            view["provenance"] = _build_provenance(app_row)
            return {"status": True, **view}, 200
        finally:
            if tmp_dir:
                shutil.rmtree(tmp_dir, ignore_errors=True)


def _identity_and_admin():
    identity = get_jwt_identity() or {}
    role = str(identity.get("role") or "")
    return identity, role.startswith("admin")


class ForensicsDeliveriesResource(Resource):
    """GET /api/forensics/deliveries?application_id= — admin or owner."""

    @jwt_required()
    def get(self):
        identity, is_admin = _identity_and_admin()
        query = DownloadDelivery.query
        application_id = request.args.get("application_id", type=int)
        if application_id:
            query = query.filter_by(application_id=application_id)
        if is_admin:
            deliveries = query.order_by(DownloadDelivery.delivery_id.desc()).all()
        else:
            number = identity.get("number")
            if not number:
                return {"status": False, "msg": "需要管理员权限"}, 403
            deliveries = query.filter_by(user_number=number).order_by(DownloadDelivery.delivery_id.desc()).all()

        items = []
        for delivery in deliveries:
            anchor = _anchor_for(delivery)
            items.append(
                {
                    "uuid": delivery.uuid,
                    "application_id": delivery.application_id,
                    "data_id": delivery.data_id,
                    "data_type": delivery.data_type,
                    "user_number": delivery.user_number,
                    "fingerprint_id": delivery.fingerprint_id,
                    "fid_short": delivery.fingerprint_id[:12],
                    "status": delivery.status,
                    "algorithm": delivery.algorithm,
                    "artifact_root": delivery.artifact_root,
                    "created_at": delivery.created_at.isoformat() if delivery.created_at else None,
                    "ready_at": delivery.ready_at.isoformat() if delivery.ready_at else None,
                    "completed_at": delivery.completed_at.isoformat() if delivery.completed_at else None,
                    "downloaded": DownloadRecord.query.filter_by(delivery_id=delivery.delivery_id).count() > 0,
                    "chain": _chain_summary(delivery.uuid),
                    "anchor": {
                        "status": anchor.status if anchor else None,
                        "batch_id": anchor.batch_id if anchor else None,
                    },
                }
            )
        return {"status": True, "deliveries": items}, 200


class ForensicsDeliveryDetailResource(Resource):
    """GET /api/forensics/deliveries/<uuid> — admin or owner. Contract-fixed shape."""

    @jwt_required()
    def get(self, delivery_uuid):
        identity, is_admin = _identity_and_admin()
        delivery = DownloadDelivery.query.filter_by(uuid=delivery_uuid).first()
        if delivery is None:
            return {"status": False, "msg": "交付不存在"}, 404
        if not is_admin and delivery.user_number != identity.get("number"):
            return {"status": False, "msg": "无权查看该交付"}, 403

        events = []
        try:
            for event in get_events(delivery.uuid):
                events.append(
                    {
                        "seq": event.seq,
                        "event_type": event.event_type,
                        "ts": event.ts.isoformat() if event.ts else None,
                        "event_hash": event.event_hash,
                        "kid": event.kid,
                    }
                )
        except Exception:
            logging.warning("event listing failed for stream %s", delivery.uuid, exc_info=True)

        anchor = _anchor_for(delivery)
        return {
            "status": True,
            "delivery": delivery.to_dict(),
            "events": events,
            "chain": _chain_full(delivery.uuid),
            "anchor": {
                "batch_id": anchor.batch_id if anchor else None,
                "status": anchor.status if anchor else None,
                "provider": anchor.provider if anchor else None,
                "root_hex": anchor.root_hex if anchor else None,
                "error": anchor.error if anchor else None,
            },
        }, 200


class ForensicsAnchorBuildResource(Resource):
    """POST /api/forensics/anchor/build — admin. Zero events maps to 400, never 500."""

    @admin_required
    @limiter.limit("10 per minute")
    def post(self):
        try:
            record = build_batch()
        except ValueError:
            return {"status": False, "msg": "暂无可锚定的证据事件"}, 400
        except Exception as e:
            logging.error("anchor build failed: %s", e, exc_info=True)
            return {"status": False, "msg": f"锚定失败: {e}"}, 500
        return {
            "status": True,
            "batch": {
                "batch_id": record.batch_id,
                "root_hex": record.root_hex,
                "status": record.status,
                "provider": record.provider,
                "error": record.error,
            },
        }, 200


class ForensicsKeyInfoResource(Resource):
    """GET /api/forensics/keyinfo — admin. Active Ed25519 signing key summary."""

    @admin_required
    def get(self):
        info = crypto_keyinfo()
        _kid, private_key = ensure_active_key()
        public_hex = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        ).hex()
        return {
            "status": True,
            "kid": info["kid"],
            "algo": "Ed25519",
            "fingerprint": info["fingerprint"],
            "public_key_hex": public_hex,
        }, 200
