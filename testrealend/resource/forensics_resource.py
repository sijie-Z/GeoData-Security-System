"""v3 forensics endpoints (contract locked with the UI line, taskbook round B §1).

  POST /api/forensics/verify              multipart file | JSON {qr_text}
  POST /api/forensics/trace               same inputs (+ optional application_id) + provenance
  GET  /api/forensics/deliveries          ?application_id=  (admin or owner)
  GET  /api/forensics/deliveries/<uuid>   (admin or owner)
  POST /api/forensics/anchor/build        (admin; optional body {"provider": "ots"|"evm"})
  GET  /api/forensics/anchors             ?page=&page_size=  (admin) batch ledger + summary
  GET  /api/forensics/anchors/<batch_id>  (admin) batch detail + coverage digest
  GET  /api/forensics/anchors/<batch_id>/proof  (admin) evidence-pack download
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
from flask import request, send_file
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource
from sqlalchemy import func

from algorithm.extract import extract as vector_extract
from algorithm.raster_dwt_watermark import extract_dwt
from algorithm.raster_histogram_watermark import extract_histogram
from algorithm.raster_reversible_watermark import decode_reversible
from algorithm.vector_dqim import SCHEME as DQIM_SCHEME
from algorithm.vector_dqim import extract_dqim as vector_extract_dqim
from crypto.keys import ensure_active_key
from crypto.keys import keyinfo as crypto_keyinfo
from crypto.payload import is_v2_text, parse_qr_text
from delivery.artifact import file_root, shp_component_root
from evidence import anchor as anchor_mod
from evidence.anchor import EVMAnchorProvider, build_batch
from evidence.chain import get_events, verify_events, verify_stream
from extension.extension import db, limiter
from model.anchor_record import AnchorRecord
from model.Application import Application
from model.download_delivery import DownloadDelivery
from model.Download_Record import DownloadRecord
from model.evidence_event import EvidenceEvent
from resource.watermark_utils import QR_SECRET_KEY, decode_qr_from_image
from resource.watermark_utils import parse_qr_text as parse_v1_lines
from utils.required import admin_required
from utils.time_fmt import utc_iso_z

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


def _vector_extractor_for(vr_data):
    """Pick the extraction algorithm for a stored vr_data record.

    ``"dqim1"`` -> the difference-domain scheme (``algorithm/vector_dqim.py``,
    translation-robust; new v3 deliveries). Anything else — legacy records have
    no ``scheme`` key — -> the absolute-coordinate ``algorithm.extract.extract``,
    so older artifacts stay verifiable unchanged.
    """
    if vr_data.get("scheme") == DQIM_SCHEME:
        return vector_extract_dqim
    return vector_extract


def _vector_side_length(vr_data, extractor):
    """Stored side_length, with each scheme's historical default as fallback."""
    return vr_data.get("side_length") or (130 if extractor is vector_extract_dqim else 45)


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
    """Latest AnchorRecord covering this delivery (created after ready_at), else None.

    Single targeted query — no full-table scan: DATETIME columns store naive
    UTC wall times, so the aware boundary is bound as naive UTC.
    """
    if delivery.ready_at is None:
        return None
    ready_naive = _as_utc(delivery.ready_at).replace(tzinfo=None)
    return (
        AnchorRecord.query.filter(AnchorRecord.created_at >= ready_naive)
        .order_by(AnchorRecord.created_at.desc(), AnchorRecord.id.desc())
        .first()
    )


# --------------------------------------------------------------------------- #
# anchor batch ledger (存证中心)                                                #
# --------------------------------------------------------------------------- #

SEPOLIA_TX_URL_PREFIX = "https://sepolia.etherscan.io/tx/"


def _anchors_root():
    """Real path of the anchors dir, read live from ``evidence.anchor`` so tests
    (which monkeypatch ``evidence.anchor.ANCHOR_DIR``) and runtime setups agree."""
    return os.path.realpath(anchor_mod.ANCHOR_DIR)


def _real_proof_path(record):
    """Realpath-validated proof file path, confined to the anchors directory.

    ``proof_path`` is written by ``build_batch`` under ``instance/anchors/``. A
    tampered or foreign row must never let a download (or an explorer-url read)
    escape that directory, so anything whose realpath falls outside the anchors
    root — or that traverses via ``..``/symlink — is treated as absent.
    """
    if not record.proof_path:
        return None
    root = _anchors_root()
    real = os.path.realpath(str(record.proof_path))
    if not (real == root or real.startswith(root + os.sep)):
        return None
    return real


def _proof_available(record):
    """True when proof_path is set, stays under the anchors root and exists on disk."""
    real = _real_proof_path(record)
    return bool(real and os.path.isfile(real))


def _explorer_url(record):
    """Sepolia Etherscan URL read back from the stored EVM evidence pack.

    The pack written by ``EVMAnchorProvider`` carries ``tx_hash``/``chain_id``;
    reading it (instead of trusting ``provider == "evm-sepolia"``) means any
    EVM-style proof with a real tx hash gets a link, and anything unreadable —
    missing file, non-JSON, no/invalid tx_hash — degrades to None.
    """
    real = _real_proof_path(record)
    if not real or not real.lower().endswith(".json") or not os.path.isfile(real):
        return None
    try:
        with open(real, encoding="utf-8") as fh:
            pack = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(pack, dict):
        return None
    tx_hash = str(pack.get("tx_hash") or "").strip()
    if not tx_hash.startswith("0x") or len(tx_hash) != 66:
        return None
    try:
        int(tx_hash[2:], 16)
    except ValueError:
        return None
    return f"{SEPOLIA_TX_URL_PREFIX}{tx_hash}"


def _anchor_view(record):
    """Whitelisted AnchorRecord view shared by the ledger list and the detail page."""
    return {
        "batch_id": record.batch_id,
        "provider": record.provider,
        "status": record.status,
        "root_hex": record.root_hex,
        "event_count": record.event_count,
        "head_hash": record.head_hash,
        "proof_sha256": record.proof_sha256,
        "proof_available": _proof_available(record),
        "error": record.error,
        "created_at": utc_iso_z(record.created_at),
        "updated_at": utc_iso_z(record.updated_at),
        "explorer_url": _explorer_url(record),
    }


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
    saw_tampered = False
    for delivery in candidates:
        vr_data = _parse_vr_data(delivery.vr_data)
        if vr_data is None:
            continue
        out_dir = tempfile.mkdtemp(prefix="fx_vec_", dir=work_root)
        extractor = _vector_extractor_for(vr_data)
        try:
            _shp_out, wm_png = extractor(
                shp_path, vr_data["vr"], side_length=_vector_side_length(vr_data, extractor), output_dir=out_dir
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
            except Exception:
                # A wrong-vr candidate can decode a corrupted copy of another
                # delivery's text; only report tampering once no candidate matches.
                saw_tampered = True
                continue
            if parsed["fid_hex"] == delivery.fingerprint_id:
                return {"kind": "v2", "delivery": delivery, "parsed": parsed, "fid_confidence": "候选交付提取一致"}
        elif V1_BANNER in text:
            return {"kind": "v1", "qr_text": text, "signature_ok": _verify_v1_hmac(text)}
    if saw_tampered:
        return {"kind": "tamper", "error": "signature verification failed for decodable v2 text"}
    return None


def _detect_raster_stego(image_path, work_root):
    """Try every READY raster delivery whose meta file is on disk, newest first."""
    candidates = (
        DownloadDelivery.query.filter_by(data_type="raster", status="READY")
        .order_by(DownloadDelivery.delivery_id.desc())
        .limit(CANDIDATE_LIMIT)
        .all()
    )
    saw_tampered = False
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
            except Exception:
                saw_tampered = True
                continue
            if parsed["fid_hex"] == delivery.fingerprint_id:
                return {"kind": "v2", "delivery": delivery, "parsed": parsed, "fid_confidence": "候选交付提取一致"}
        elif V1_BANNER in text:
            return {"kind": "v1", "qr_text": text, "signature_ok": _verify_v1_hmac(text)}
    if saw_tampered:
        return {"kind": "tamper", "error": "signature verification failed for decodable v2 text"}
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
        "found": False,
        "watermark_version": 0,
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
        msg += "，产物根一致" if artifact_match else "，但产物根不一致（artifact_root_match=false）"
    return {
        "found": True,
        "watermark_version": 2,
        "fid": delivery.fingerprint_id,
        "fid_short": delivery.fingerprint_id[:12],
        "delivery_uuid": delivery.uuid,
        "data_alias": app_row.data_alias if app_row else None,
        "data_type": delivery.data_type,
        "issued_at": utc_iso_z(delivery.created_at),
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
    extractor = _vector_extractor_for(vr_data)
    try:
        _shp, wm_png = extractor(
            vector_path, vr_data["vr"], side_length=_vector_side_length(vr_data, extractor), output_dir=out_dir
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
        # Bounded result set: default 200, clamp invalid/out-of-range to 200.
        limit = request.args.get("limit", default=200, type=int)
        if limit is None or limit < 1 or limit > 1000:
            limit = 200
        if is_admin:
            deliveries = query.order_by(DownloadDelivery.delivery_id.desc()).limit(limit).all()
        else:
            number = identity.get("number")
            if not number:
                return {"status": False, "msg": "需要管理员权限"}, 403
            deliveries = (
                query.filter_by(user_number=number).order_by(DownloadDelivery.delivery_id.desc()).limit(limit).all()
            )

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
                    "created_at": utc_iso_z(delivery.created_at),
                    "ready_at": utc_iso_z(delivery.ready_at),
                    "completed_at": utc_iso_z(delivery.completed_at),
                    "downloaded": DownloadRecord.query.filter_by(delivery_id=delivery.delivery_id).count() > 0,
                    "chain": _chain_summary(delivery.uuid),
                    "anchor": {
                        "status": anchor.status if anchor else None,
                        "batch_id": anchor.batch_id if anchor else None,
                    },
                }
            )
        return {"status": True, "deliveries": items}, 200


class ForensicsDeliveryStatsResource(Resource):
    """GET /api/forensics/deliveries/stats — admin.

    Live aggregate for the delivery board: the list endpoint above costs N+2
    queries per row (chain + anchor per delivery), so it must not be a polling
    source. Everything here is aggregate SQL except two bounded pieces:

    * ``anchor`` mirrors ``_anchor_for`` batch-wise: the latest AnchorRecord
      covers every delivery with ``ready_at <= created_at`` (an anchor is a
      cumulative snapshot), so the bucket is decided by that one record.
    * ``chain`` validity is checked over a SAMPLE of the latest 200 deliveries,
      whose events are fetched in ONE batched query and verified per stream
      with the pure ``verify_events`` (no per-row ``verify_stream`` queries).
      ``chain_checked`` reports the sample size; a stream with no events is
      "valid" exactly as ``verify_stream`` reports it.
    """

    CHAIN_SAMPLE_LIMIT = 200

    @jwt_required()
    def get(self):
        _identity, is_admin = _identity_and_admin()
        if not is_admin:
            return {"status": False, "msg": "需要管理员权限"}, 403

        total = db.session.query(func.count(DownloadDelivery.delivery_id)).scalar() or 0

        by_status = [
            {"status": row[0] or "unknown", "count": int(row[1])}
            for row in db.session.query(DownloadDelivery.status, func.count()).group_by(DownloadDelivery.status).all()
        ]

        algo_col = func.coalesce(DownloadDelivery.algorithm, "unknown")
        by_algorithm = [
            {"algorithm": row[0], "count": int(row[1])}
            for row in db.session.query(algo_col, func.count()).group_by(algo_col).all()
        ]

        type_col = func.coalesce(DownloadDelivery.data_type, "unknown")
        by_data_type = [
            {"data_type": row[0], "count": int(row[1])}
            for row in db.session.query(type_col, func.count()).group_by(type_col).all()
        ]

        downloaded_count = (
            db.session.query(func.count(func.distinct(DownloadRecord.delivery_id)))
            .filter(DownloadRecord.delivery_id.isnot(None))
            .scalar()
            or 0
        )

        # anchor buckets: batch equivalent of _anchor_for (latest covering
        # anchor decides), without one query per delivery.
        anchor_buckets = {"submitted": 0, "pending": 0, "none": int(total)}
        latest_anchor = AnchorRecord.query.order_by(AnchorRecord.created_at.desc(), AnchorRecord.id.desc()).first()
        if latest_anchor is not None and latest_anchor.created_at is not None:
            covered = (
                db.session.query(func.count())
                .select_from(DownloadDelivery)
                .filter(
                    DownloadDelivery.ready_at.isnot(None),
                    DownloadDelivery.ready_at <= latest_anchor.created_at,
                )
                .scalar()
                or 0
            )
            bucket = "submitted" if str(latest_anchor.status or "").upper() == "SUBMITTED" else "pending"
            anchor_buckets = {
                "submitted": int(covered) if bucket == "submitted" else 0,
                "pending": int(covered) if bucket == "pending" else 0,
                "none": int(total) - int(covered),
            }

        # chain validity over the latest CHAIN_SAMPLE_LIMIT deliveries, events
        # fetched in one batched query.
        sample_uuids = [
            row[0]
            for row in DownloadDelivery.query.with_entities(DownloadDelivery.uuid)
            .order_by(DownloadDelivery.delivery_id.desc())
            .limit(self.CHAIN_SAMPLE_LIMIT)
            .all()
        ]
        chain_valid_count = 0
        if sample_uuids:
            stream_events = {}
            for event in (
                EvidenceEvent.query.filter(EvidenceEvent.stream_id.in_(sample_uuids))
                .order_by(EvidenceEvent.stream_id.asc(), EvidenceEvent.seq.asc())
                .all()
            ):
                stream_events.setdefault(event.stream_id, []).append(event)
            for stream_id in sample_uuids:
                if verify_events(stream_events.get(stream_id, []))["valid"]:
                    chain_valid_count += 1

        recent = [
            {
                "uuid": row.uuid,
                "fid_short": (row.fingerprint_id or "")[:12] or None,
                "user_number": row.user_number,
                "status": row.status,
                "created_at": utc_iso_z(row.created_at),
            }
            for row in DownloadDelivery.query.order_by(DownloadDelivery.delivery_id.desc()).limit(10).all()
        ]

        return {
            "status": True,
            "stats": {
                "total": int(total),
                "by_status": by_status,
                "by_algorithm": by_algorithm,
                "by_data_type": by_data_type,
                "downloaded_count": int(downloaded_count),
                "anchor": anchor_buckets,
                "chain_valid_count": chain_valid_count,
                "chain_checked": len(sample_uuids),
                "recent": recent,
            },
        }, 200


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
                        "ts": utc_iso_z(event.ts),
                        "event_hash": event.event_hash,
                        "kid": event.kid,
                    }
                )
        except Exception:
            logging.warning("event listing failed for stream %s", delivery.uuid, exc_info=True)

        anchor = _anchor_for(delivery)
        # Explicit whitelist — never hand out the raw to_dict(). Internal
        # personalization material (vr_data extraction basis, artifact paths)
        # is admin-only: relaying it to the artifact holder would weaken the
        # anti-copy / anti-tamper evidence position.
        delivery_view = {
            "delivery_id": delivery.delivery_id,
            "uuid": delivery.uuid,
            "application_id": delivery.application_id,
            "data_id": delivery.data_id,
            "data_type": delivery.data_type,
            "user_number": delivery.user_number,
            "fingerprint_id": delivery.fingerprint_id,
            "status": delivery.status,
            "algorithm": delivery.algorithm,
            "artifact_root": delivery.artifact_root,
            "error": delivery.error,
            "created_at": utc_iso_z(delivery.created_at),
            "ready_at": utc_iso_z(delivery.ready_at),
            "completed_at": utc_iso_z(delivery.completed_at),
        }
        if is_admin:
            delivery_view["artifact_path"] = delivery.artifact_path
            delivery_view["vr_data"] = delivery.vr_data
            delivery_view["artifact_meta_path"] = delivery.artifact_meta_path
        return {
            "status": True,
            "delivery": delivery_view,
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
    """POST /api/forensics/anchor/build — admin. Zero events maps to 400, never 500.

    Optional JSON body ``{"provider": "ots" | "evm"}`` picks the anchor backend
    (default "ots", backward compatible). The batch gains ``explorer_url`` once
    an EVM tx hash + contract address are known (Sepolia Etherscan), else null.
    """

    @admin_required
    @limiter.limit("10 per minute")
    def post(self):
        body = request.get_json(silent=True) or {}
        provider_name = str(body.get("provider") or "ots").strip().lower()
        provider = EVMAnchorProvider() if provider_name == "evm" else None
        try:
            record = build_batch(provider=provider)
        except ValueError:
            return {"status": False, "msg": "暂无可锚定的证据事件"}, 400
        except Exception as e:
            logging.error("anchor build failed: %s", e, exc_info=True)
            return {"status": False, "msg": f"锚定失败: {e}"}, 500
        proof_meta = getattr(record, "proof_meta", None) or {}
        explorer_url = None
        if record.provider == "evm-sepolia" and proof_meta.get("tx_hash") and proof_meta.get("contract"):
            explorer_url = f"https://sepolia.etherscan.io/tx/{proof_meta['tx_hash']}"
        return {
            "status": True,
            "batch": {
                "batch_id": record.batch_id,
                "root_hex": record.root_hex,
                "status": record.status,
                "provider": record.provider,
                "error": record.error,
                "explorer_url": explorer_url,
            },
        }, 200


class ForensicsAnchorsResource(Resource):
    """GET /api/forensics/anchors?page=&page_size= — admin. Batch ledger.

    ``summary`` covers the whole table (not just the page) so the UI hero band
    can aggregate without a second endpoint; provider/status keys are read from
    the data (``opentimestamps``/``evm-sepolia``/…), unknown values included.
    """

    @admin_required
    def get(self):
        page = request.args.get("page", default=1, type=int)
        page_size = request.args.get("page_size", default=20, type=int)
        if page is None or page < 1:
            page = 1
        if page_size is None or page_size < 1:
            page_size = 20
        page_size = min(page_size, 100)

        query = AnchorRecord.query.order_by(AnchorRecord.created_at.desc(), AnchorRecord.id.desc())
        total = query.count()
        records = query.offset((page - 1) * page_size).limit(page_size).all()

        by_provider = {
            (row[0] or "unknown"): int(row[1])
            for row in db.session.query(AnchorRecord.provider, func.count()).group_by(AnchorRecord.provider).all()
        }
        by_status = {
            (row[0] or "unknown"): int(row[1])
            for row in db.session.query(AnchorRecord.status, func.count()).group_by(AnchorRecord.status).all()
        }
        return {
            "status": True,
            "anchors": [_anchor_view(record) for record in records],
            "summary": {
                "total": int(total),
                "by_provider": by_provider,
                "by_status": by_status,
            },
            "pages": {"total": int(total), "page": page, "page_size": page_size},
        }, 200


class ForensicsAnchorDetailResource(Resource):
    """GET /api/forensics/anchors/<batch_id> — admin. Batch detail.

    ``events_digest`` documents batch coverage: ``build_batch`` anchors a SNAPSHOT
    of every evidence event as of creation (ordered by insertion id), so the
    coverage statement is ``included_event_count`` + ``head_hash`` — there is no
    per-batch event list to hand out.
    """

    @admin_required
    def get(self, batch_id):
        record = AnchorRecord.query.filter_by(batch_id=batch_id).first()
        if record is None:
            return {"status": False, "msg": "批次不存在"}, 404
        return {
            "status": True,
            "anchor": _anchor_view(record),
            "events_digest": {
                "semantics": "snapshot_all_events",
                "included_event_count": record.event_count,
                "head_hash": record.head_hash,
            },
        }, 200


class ForensicsAnchorProofResource(Resource):
    """GET /api/forensics/anchors/<batch_id>/proof — admin. Evidence-pack download.

    Path-traversal guard: the stored ``proof_path`` must realpath inside the
    anchors directory, else 404 (as does a missing file). Download name is
    normalized to ``<batch_id>.proof.json`` / ``<batch_id>.ots``.
    """

    @admin_required
    def get(self, batch_id):
        record = AnchorRecord.query.filter_by(batch_id=batch_id).first()
        if record is None:
            return {"status": False, "msg": "批次不存在"}, 404
        real = _real_proof_path(record)
        if not real or not os.path.isfile(real):
            return {"status": False, "msg": "证据文件不存在"}, 404
        is_json = real.lower().endswith(".json")
        download_name = f"{batch_id}.proof.json" if is_json else f"{batch_id}.ots"
        return send_file(
            real,
            as_attachment=True,
            download_name=download_name,
            mimetype="application/json" if is_json else "application/octet-stream",
        )


class ForensicsKeyInfoResource(Resource):
    """GET /api/forensics/keyinfo — admin. Active Ed25519 signing key summary."""

    @admin_required
    def get(self):
        info = crypto_keyinfo()
        _kid, private_key = ensure_active_key()
        public_hex = (
            private_key.public_key()
            .public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
            .hex()
        )
        return {
            "status": True,
            "kid": info["kid"],
            "algo": "Ed25519",
            "fingerprint": info["fingerprint"],
            "public_key_hex": public_hex,
        }, 200
