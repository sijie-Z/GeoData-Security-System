"""v3 delivery personalization service.

Ties together: base-file resolution (same precedence as the legacy download
path: watermark_path -> data_url -> Shp -> RasterData), v2 QR rendering,
embedding via the existing algorithms, artifact hashing and evidence events.

Discipline:
  - evidence writes never block business flow (try/except + log);
  - the delivery row is marked FAILED and the exception re-raised when
    personalization cannot honestly produce an artifact (the API answers 500);
  - format gate: bases that are not geo formats degrade to ``passthrough``
    (artifact = byte copy, no fingerprint) instead of failing.
"""

import json
import logging
import os
import secrets
import shutil
import zipfile
from datetime import UTC, datetime, timedelta

from flask import current_app
from PIL import Image

from algorithm.embed import embed as vector_embed
from algorithm.raster_reversible_watermark import embed_reversible
from crypto.keys import ensure_active_key
from crypto.payload import build_qr_v2_text
from delivery.artifact import file_root, shp_component_root
from delivery.qr2 import render_v2_qr_png
from evidence.chain import append_event
from extension.extension import db
from model.download_delivery import DownloadDelivery
from model.download_token import DownloadToken
from model.Raster_Data import RasterData
from model.Shp_Data import Shp

TOKEN_TTL = timedelta(hours=1)

# E1-measured reliability floor: at box_size=2 the vector chain only decoded
# reliably once every embedding chunk received >=4 votes on the average
# (lambda>=4 passed, lambda=3 produced an undecodable artifact — see the E1
# report). Enforced here so undecodable artifacts fail honestly at 500 instead
# of being delivered silently.
MIN_VOTES_PER_CHUNK = 4

RASTER_EXTS = {".tif", ".tiff", ".png", ".jpg", ".jpeg"}
SHP_COMPONENT_EXTS = (".shp", ".shx", ".dbf", ".prj", ".cpg")


class DeliveryError(Exception):
    """Personalization cannot honestly produce an artifact for this delivery."""


def _log_event(stream_id, event_type, payload):
    """Best-effort evidence append — never blocks business flow."""
    try:
        append_event(stream_id, event_type, payload)
    except Exception:
        # A failed append (e.g. commit error) leaves the session in a failed
        # state; roll back so the caller's next business commit cannot die with
        # PendingRollbackError because of an optional evidence write.
        db.session.rollback()
        logging.warning("evidence append failed: stream=%s type=%s", stream_id, event_type, exc_info=True)


def _resolve_existing_path(path_value):
    """Same resolution rules as resource.download_file_resource._resolve_existing_path."""
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


def resolve_base_file(application_row):
    """First existing base file, in the legacy download-path precedence order."""
    candidate_paths = [application_row.watermark_path, application_row.data_url]
    shp = db.session.get(Shp, application_row.data_id)
    if shp:
        candidate_paths.extend([shp.shp_file_path, shp.url])
    raster = db.session.get(RasterData, application_row.data_id)
    if raster:
        candidate_paths.extend([raster.raster_file_path, raster.url])
    for path_value in candidate_paths:
        resolved = _resolve_existing_path(path_value)
        if resolved and os.path.isfile(resolved):
            return resolved
    return None


def _safe_unzip(zip_path, extract_dir):
    """Defensive extraction for base zips (they are our own artifacts, but cheap to guard)."""
    real_root = os.path.realpath(extract_dir)
    with zipfile.ZipFile(zip_path) as zf:
        infos = zf.infolist()
        if len(infos) > 50:
            raise ValueError("压缩包成员数超过 50，拒绝解压")
        total = 0
        for info in infos:
            norm = info.filename.replace("\\", "/")
            parts = [p for p in norm.split("/") if p not in ("", ".")]
            if norm.startswith("/") or (len(norm) > 1 and norm[1] == ":") or ".." in parts:
                raise ValueError(f"非法文件路径: {info.filename}")
            total += info.file_size
        if total > 300 * 1024 * 1024:
            raise ValueError("解压总量超过 300MB，拒绝解压")
        for info in infos:
            target = os.path.realpath(os.path.join(extract_dir, info.filename.replace("\\", "/")))
            if not (target == real_root or target.startswith(real_root + os.sep)):
                raise ValueError(f"非法文件路径: {info.filename}")
        os.makedirs(extract_dir, exist_ok=True)
        zf.extractall(extract_dir)


def _find_shp_file(directory):
    """A .shp counts only when its .shx and .dbf siblings exist.

    Same criterion as forensics ``_find_vector_base``: a shapefile missing its
    components would produce a "delivered" artifact that can never be verified
    again, so such zips degrade to passthrough instead.
    """
    for root, _dirs, files in os.walk(directory):
        names = {name.lower() for name in files}
        for name in sorted(files):
            if not name.lower().endswith(".shp"):
                continue
            stem = name[:-4].lower()
            if f"{stem}.shx" in names and f"{stem}.dbf" in names:
                return os.path.join(root, name)
    return None


def _classify_base(base_path, product_dir):
    """Return ``(kind, payload)`` with kind in {"vector","raster","passthrough"}.

    vector: payload is a .shp path (a base zip carrying a shapefile is unpacked
    into ``product_dir`` first); raster: payload is the host path.
    """
    ext = os.path.splitext(base_path)[1].lower()
    if ext == ".zip":
        unpack_dir = os.path.join(product_dir, "base_unpacked")
        try:
            _safe_unzip(base_path, unpack_dir)
        except Exception as e:
            logging.warning("base zip unpack failed (%s): %s", base_path, e)
            return "passthrough", base_path
        shp_path = _find_shp_file(unpack_dir)
        if shp_path:
            return "vector", shp_path
        return "passthrough", base_path
    if ext == ".shp":
        stem = os.path.splitext(base_path)[0]
        if all(os.path.exists(f"{stem}{suffix}") for suffix in (".shx", ".dbf")):
            return "vector", base_path
        return "passthrough", base_path
    if ext in RASTER_EXTS:
        return "raster", base_path
    return "passthrough", base_path


def _build_qr_text(delivery_row):
    kid, _private_key = ensure_active_key()
    now_epoch = int(datetime.now(UTC).timestamp())
    return build_qr_v2_text(delivery_row.fingerprint_id, delivery_row.delivery_id, kid, now_epoch), kid


def _personalize_vector(delivery_row, shp_path, product_dir):
    text, _kid = _build_qr_text(delivery_row)
    png_path = os.path.join(product_dir, "qr_v2.png")
    render_v2_qr_png(text, png_path)

    result = vector_embed(shp_path, png_path, output_dir=product_dir)
    capacity = result.get("capacity_report") or {}
    needed = int(capacity.get("needed_chunks") or 0)
    available = int(capacity.get("available_chunks") or 0)
    # Fail-closed: a missing/empty capacity report is not a pass.
    if needed <= 0:
        raise DeliveryError("嵌入容量报告缺失 needed_chunks，拒绝交付（fail-closed）")
    if available < MIN_VOTES_PER_CHUNK * needed:
        raise DeliveryError(
            f"顶点预算不足以保证可靠提取：需要至少 {MIN_VOTES_PER_CHUNK * needed} 个顶点"
            f"（每区块平均投票 {available / needed:.2f}，实测可靠下限 {MIN_VOTES_PER_CHUNK}），"
            f"当前仅 {available} 个"
        )
    delivery_row.algorithm = "vector"
    delivery_row.artifact_path = result["zip_path"]
    delivery_row.vr_data = json.dumps({"vr": result["vr"], "side_length": result["side_length"]})
    delivery_row.artifact_root = shp_component_root(result["zip_path"])


def _personalize_raster(delivery_row, host_path, product_dir):
    text, _kid = _build_qr_text(delivery_row)
    png_path = os.path.join(product_dir, "qr_v2.png")
    render_v2_qr_png(text, png_path)

    with Image.open(png_path) as qr_img:
        result = embed_reversible(
            host_path=host_path,
            watermark_img=qr_img,
            output_dir=product_dir,
            prefix=f"delivery_{delivery_row.uuid[:8]}",
        )
    delivery_row.algorithm = "lsb"
    delivery_row.artifact_path = result["stego_path"]
    delivery_row.artifact_meta_path = result["wm_meta_path"]
    delivery_row.artifact_root = file_root(result["stego_path"])


def personalize_delivery(delivery_row, application_row):
    """PENDING -> PROCESSING -> READY (or FAILED + raise on honest failure)."""
    product_dir = None
    try:
        delivery_row.status = "PROCESSING"
        db.session.commit()

        product_dir = os.path.join(current_app.config["DELIVERY_FOLDER"], delivery_row.uuid)
        os.makedirs(product_dir, exist_ok=True)

        base_path = resolve_base_file(application_row)
        if not base_path:
            raise DeliveryError("未找到可个性化交付的基地文件")

        kind, payload = _classify_base(base_path, product_dir)
        if kind == "vector":
            _personalize_vector(delivery_row, payload, product_dir)
        elif kind == "raster":
            _personalize_raster(delivery_row, payload, product_dir)
        else:
            artifact_path = os.path.join(product_dir, os.path.basename(base_path))
            shutil.copy2(base_path, artifact_path)
            delivery_row.algorithm = "passthrough"
            delivery_row.artifact_path = artifact_path
            delivery_row.artifact_root = file_root(artifact_path)
            delivery_row.error = "非地理格式，跳过指纹"

        delivery_row.status = "READY"
        delivery_row.ready_at = datetime.now(UTC)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # The failure may have happened after vector_embed already wrote its
        # product into product_dir (e.g. the lambda gate) — never leave orphan
        # artifacts behind for a delivery that will never be served.
        if product_dir:
            shutil.rmtree(product_dir, ignore_errors=True)
        delivery_row.status = "FAILED"
        delivery_row.error = str(e)[:255]
        db.session.commit()
        raise

    _log_event(
        delivery_row.uuid,
        "PersonalizationCompleted",
        {"algorithm": delivery_row.algorithm or "unknown", "artifact_root": delivery_row.artifact_root or ""},
    )


def record_download_event(delivery_row, ip, filename, token_prefix=""):
    """DownloadCompleted evidence + one-time completed_at stamp (best effort)."""
    try:
        _log_event(
            delivery_row.uuid,
            "DownloadCompleted",
            {"token_prefix": token_prefix or "", "ip": ip or "", "filename": filename or ""},
        )
        if delivery_row.completed_at is None:
            delivery_row.completed_at = datetime.now(UTC)
            db.session.commit()
    except Exception:
        logging.warning("record_download_event failed for delivery %s", delivery_row.uuid, exc_info=True)


def get_or_create_for_token(application_row, user_number):
    """Return ``(token, delivery, reused)``.

    Reuses an unused, unexpired token whose delivery is READY; otherwise creates
    a fresh delivery (fid + DeliveryCreated/FingerprintIssued events) + token.
    A token whose delivery FAILED is ignored and a new one is issued.

    Concurrency: there is no mutual exclusion — two simultaneous requests for
    the same (application, user) can both miss the reuse branch and each build
    their own delivery with a full personalization pass. This is known
    behavior: the extra deliveries are still valid, independently auditable,
    and only the last issued token is typically used.
    """
    now = datetime.now(UTC)
    existing = (
        DownloadToken.query.filter_by(application_id=application_row.id, user_number=user_number, is_used=False)
        .filter(DownloadToken.expires_at > now)
        .order_by(DownloadToken.id.desc())
        .first()
    )
    if existing is not None and existing.delivery_id is not None:
        delivery = db.session.get(DownloadDelivery, existing.delivery_id)
        if delivery is not None and delivery.status == "READY":
            return existing, delivery, True

    delivery = DownloadDelivery(
        application_id=application_row.id,
        data_id=application_row.data_id,
        data_type=(application_row.data_type or "vector"),
        user_number=user_number,
        fingerprint_id=secrets.token_bytes(16).hex(),
        status="PENDING",
    )
    db.session.add(delivery)
    db.session.commit()

    kid, _private_key = ensure_active_key()
    _log_event(
        delivery.uuid,
        "DeliveryCreated",
        {
            "application_id": application_row.id,
            "data_id": application_row.data_id,
            "user_number": user_number,
            "fid": delivery.fingerprint_id,
        },
    )
    _log_event(delivery.uuid, "FingerprintIssued", {"fid": delivery.fingerprint_id, "kid": kid})

    personalize_delivery(delivery, application_row)

    token = DownloadToken(
        application_id=application_row.id,
        user_number=user_number,
        delivery_id=delivery.delivery_id,
        expires_at=now + TOKEN_TTL,
    )
    db.session.add(token)
    db.session.commit()
    return token, delivery, False
