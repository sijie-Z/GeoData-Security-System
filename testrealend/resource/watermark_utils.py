"""Shared utilities for watermark resources."""

import hashlib
import hmac
import logging
import os
from datetime import UTC, datetime

from PIL import Image


def safe_extract_zip(zip_ref, extract_dir):
    """安全解压ZIP，防止路径穿越攻击"""
    for member in zip_ref.namelist():
        target = os.path.realpath(os.path.join(extract_dir, member))
        if not target.startswith(os.path.realpath(extract_dir)):
            raise ValueError(f"非法文件路径: {member}")
    zip_ref.extractall(extract_dir)


# Secret key for QR signature
QR_SECRET_KEY = os.environ.get("QR_SECRET_KEY")
if not QR_SECRET_KEY:
    if os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes"):
        logging.warning("QR_SECRET_KEY not set — using dev fallback. Set this env var in production.")
        QR_SECRET_KEY = "dev-only-qr-key-replace-in-production"
    else:
        logging.error("QR_SECRET_KEY not set in production! QR signatures will be insecure.")
        QR_SECRET_KEY = "INSECURE-PRODUCTION-FALLBACK-SET-ENV-VAR"


def decode_qr_from_image(image_path):
    """Decode QR code from image file. Returns decoded text or None."""
    try:
        from pyzbar.pyzbar import decode as pyzbar_decode

        decoded_objects = pyzbar_decode(Image.open(image_path))
        if decoded_objects:
            return decoded_objects[0].data.decode("utf-8")
    except Exception:
        pass
    try:
        import cv2

        img = cv2.imread(image_path)
        if img is not None:
            detector = cv2.QRCodeDetector()
            decoded, _, _ = detector.detectAndDecode(img)
            if decoded:
                return decoded
    except Exception:
        pass
    return None


def parse_qr_text(qr_text):
    """Parse QR text into structured data dict."""
    result = {"_raw": qr_text}
    for line in qr_text.split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


def build_qr_text(item, payload):
    """Build QR code content with full traceability chain including approver info"""
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

    if item.adm2_statu is True:
        app_status = "Approved"
    elif item.adm2_statu is False:
        app_status = "Rejected"
    elif item.adm1_statu is True:
        app_status = "Adm1Approved"
    elif item.adm1_statu is False:
        app_status = "Adm1Rejected"
    else:
        app_status = "Pending"

    lines = [
        "=== SPATIAL DATA TRACKING SYSTEM ===",
        f"AppID: {item.id}",
        f"AppNumber: APP-{item.id:04d}",
        f"AppStatus: {app_status}",
        f"Data: {item.data_alias}",
        f"DataID: {item.data_id}",
        f"DataType: {item.data_type or 'vector'}",
        f"Applicant: {item.applicant_name}",
        f"ApplicantID: {item.applicant_user_number}",
        f"SubmitTime: {item.application_submission_time.strftime('%Y-%m-%d %H:%M:%S UTC') if item.application_submission_time else 'N/A'}",
        f"Adm1Name: {item.adm1_name or 'N/A'}",
        f"Adm1ID: {item.adm1_user_number or 'N/A'}",
        f"Adm1Time: {item.adm1_approval_time.strftime('%Y-%m-%d %H:%M:%S UTC') if item.adm1_approval_time else 'N/A'}",
        f"Adm2Name: {item.adm2_name or 'N/A'}",
        f"Adm2ID: {item.adm2_user_number or 'N/A'}",
        f"Adm2Time: {item.adm2_approval_time.strftime('%Y-%m-%d %H:%M:%S UTC') if item.adm2_approval_time else 'N/A'}",
        f"GenTime: {timestamp}",
    ]

    optional_fields = ["purpose", "usage_scope", "security_level", "custom_tag", "reason"]
    for key in optional_fields:
        value = payload.get(key)
        if value and str(value).strip():
            lines.append(f"{key.replace('_', ' ').title()}: {str(value).strip()}")

    content_to_sign = "\n".join(lines)
    signature = hmac.new(QR_SECRET_KEY.encode(), content_to_sign.encode(), hashlib.sha256).hexdigest()[:16]

    lines.append(f"Signature: {signature}")
    lines.append("=== END ===")

    return "\n".join(lines), signature


def get_qr_version(content_length):
    """Auto-detect QR version based on content length"""
    version_capacities = [
        25,
        47,
        77,
        114,
        154,
        195,
        224,
        279,
        335,
        395,
        468,
        535,
        619,
        667,
        758,
        854,
        938,
        1046,
        1153,
        1249,
        1358,
        1468,
        1588,
        1704,
        1863,
        2020,
        2121,
        2303,
        2431,
        2563,
    ]
    for i, capacity in enumerate(version_capacities):
        if content_length <= capacity:
            return i + 1
    return 40
