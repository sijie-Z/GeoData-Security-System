"""Blind watermark compact-payload channel (functional-gap fix, taskbook §1).

The blind algorithm (DWT-DCT-SVD via blind_watermark 0.4.4) embeds ONE bit
per 8x8 host pixel block, so the payload must stay below H*W/64 bits. The
production QR bitmap rendered for display (box_size=10, ECC M) measures
890x890 px / 792,100 bits for a typical 447-byte v1 text on this machine —
hopeless on any realistic raster. The blind dispatch therefore re-renders
the persisted QR text (application.qr_text) as a compact QR (box_size=1,
ECC L, border 4 -> 81x81 px / 6,561 bits for the same text) and embeds that.

Honest boundaries pinned by these tests (measured, not polished):
- 1024x1024 host = 16,384 blocks -> compact payload fits (utilization ~40%)
  -> 200 (the same request used to fail with a capacity 400).
- 512x512 host = 4,096 blocks -> still overflows (6,561 > 4,095) -> 400 whose
  message points at the >=1024x1024 requirement. That is the algorithm's real
  boundary, kept unpolished.
- Legacy applications without qr_text -> 400 "该申请未记录二维码文本...".
"""

import base64
import io
import json
import os
import shutil

import numpy as np
import qrcode
import rasterio
from rasterio.transform import from_bounds

FIXTURE_BOUNDS = (119.9, 29.9, 120.1, 30.1)

# Exact "legacy row" message specified by the taskbook (§1.2).
NO_QR_TEXT_MSG = "该申请未记录二维码文本，无法使用盲水印；请重新生成水印后再试"


def _make_geotiff(path, size=1024):
    """A real, georeferenced 3-band uint8 GeoTIFF (same shape as test_raster)."""
    rng = np.random.default_rng(11)
    data = (rng.random((3, size, size)) * 255).astype("uint8")
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=size,
        height=size,
        count=3,
        dtype="uint8",
        crs="EPSG:4326",
        transform=from_bounds(*FIXTURE_BOUNDS, size, size),
    ) as dst:
        dst.write(data)
    return str(path)


def _read_meta(path):
    with open(path, encoding="utf-8") as fp:
        return json.load(fp)


def _compact_qr_side(qr_text):
    """Independent reimplementation of the compact render contract
    (box_size=1, ECC L, border 4) — the expected embedded bitmap side."""
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=1, border=4)
    qr.add_data(qr_text)
    qr.make(fit=True)
    return qr.make_image().size[0]


def _seed_application(db, data_type="raster", alias="qrtext-app"):
    """A bare approved application row (no data files needed)."""
    from model.Application import Application

    item = Application(
        data_id=90001,
        data_name=alias,
        data_alias=alias,
        data_type=data_type,
        applicant_name="Tester",
        applicant_user_number="E001",
        reason="qr_text persistence",
        adm1_statu=True,
        adm2_statu=True,
    )
    db.session.add(item)
    db.session.commit()
    return item


def _seed_raster_app(db, tif_path, alias):
    """An approved raster application backed by *tif_path* on disk."""
    from flask import current_app

    from model.Application import Application
    from model.Raster_Data import RasterData

    record = RasterData(name=alias, alias=alias, raster_file_path=str(tif_path), url="", layer="")
    db.session.add(record)
    db.session.commit()
    item = Application(
        data_id=record.id,
        data_name=alias,
        data_alias=alias,
        data_type="raster",
        applicant_name="Tester",
        applicant_user_number="E001",
        reason="blind compact test",
        adm1_statu=True,
        adm2_statu=True,
    )
    db.session.add(item)
    db.session.commit()
    # Clear stale runtime artifacts so endpoint discovery is deterministic.
    shutil.rmtree(os.path.join(current_app.root_path, "runtime", "crmark", f"app_{item.id}"), ignore_errors=True)
    return item, str(tif_path)


class TestQrTextPersistence:
    """The four generation points must store build_qr_text()'s output in
    application.qr_text (the compact blind payload source)."""

    def test_raster_generate_persists_qr_text(self, client, db, auth_headers):
        from model.Application import Application

        item = _seed_application(db, data_type="raster", alias="qrtext-raster")
        resp = client.post(
            "/api/generate_raster_watermark",
            json={"application_id": item.id, "reason": "persist raster"},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.get_data(as_text=True)
        qr_text = resp.get_json()["qr_text"]
        assert qr_text and "Signature:" in qr_text

        db.session.expire_all()
        row = db.session.get(Application, item.id)
        assert row.qr_text == qr_text
        assert row.qrcode  # the box_size=10 display bitmap stays for the other algorithms

    def test_vector_generate_persists_qr_text(self, client, db, auth_headers):
        from model.Application import Application

        item = _seed_application(db, data_type="vector", alias="qrtext-vector")
        resp = client.post(
            "/api/generate_watermark",
            json={"application_id": item.id, "reason": "persist vector"},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.get_data(as_text=True)
        qr_text = resp.get_json()["qr_text"]
        assert qr_text and "Signature:" in qr_text

        db.session.expire_all()
        row = db.session.get(Application, item.id)
        assert row.qr_text == qr_text

    def test_batch_generate_persists_qr_text(self, client, db, auth_headers):
        from model.Application import Application

        item = _seed_application(db, data_type="raster", alias="qrtext-batch")
        resp = client.post(
            "/api/watermark/batch_generate",
            json={"application_ids": [item.id], "reason": "persist batch"},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.get_data(as_text=True)
        assert resp.get_json()["summary"]["success"] == 1, resp.get_json()

        db.session.expire_all()
        row = db.session.get(Application, item.id)
        assert row.qr_text and "Signature:" in row.qr_text


class TestBlindCompactEmbed:
    """The blind dispatch must embed the compact re-render of qr_text."""

    def test_blind_embed_1024_roundtrip(self, client, db, auth_headers, adm2_headers, adm3_headers, tmp_path):
        from model.Application import Application

        host = _make_geotiff(tmp_path / "host_1024.tif", 1024)
        item, _ = _seed_raster_app(db, host, "blind-compact-1024")

        gen = client.post(
            "/api/generate_raster_watermark",
            json={"application_id": item.id, "reason": "blind compact roundtrip"},
            headers=auth_headers,
        )
        assert gen.status_code == 200, gen.get_data(as_text=True)
        qr_text = gen.get_json()["qr_text"]

        # Pre-fix this request used the persisted box_size=10 bitmap
        # (792,100 bits) and failed with a capacity 400 on any host.
        resp = client.post(
            "/api/embedding_watermark",
            json={"application_id": item.id, "algorithm": "blind"},
            headers=adm2_headers,
        )
        assert resp.status_code == 200, resp.get_data(as_text=True)

        db.session.expire_all()
        row = db.session.get(Application, item.id)
        assert row.watermark_embedded is True
        stego, meta_path = row.watermark_path, row.watermark_path_meta
        assert stego and os.path.isfile(stego), stego
        assert os.path.isfile(meta_path)
        meta = _read_meta(meta_path)
        assert meta["algorithm"] == "blind_watermark"
        assert meta["capacity"]["block_num"] == 16384  # 1024x1024 -> H*W/64
        assert meta["watermark"]["bit_count"] < meta["capacity"]["block_num"]
        with rasterio.open(stego) as src:
            assert src.crs is not None and src.crs.to_epsg() == 4326

        # The embedded bitmap is exactly the compact QR of the persisted text
        # (81x81 px measured for this text), not the 890x890 display render.
        expected_side = _compact_qr_side(qr_text)
        assert meta["watermark"]["width"] == expected_side
        assert meta["watermark"]["height"] == expected_side

        # Usability: extraction recovers the signed QR text (digest + HMAC).
        with open(stego, "rb") as fh:
            ex = client.post(
                "/api/vector/extract",
                data={"application_id": str(item.id), "file": (fh, os.path.basename(stego))},
                headers=adm3_headers,
                content_type="multipart/form-data",
            )
        assert ex.status_code == 200, ex.get_data(as_text=True)
        verify = ex.get_json()["data"]["decoded_info"]["verify"]
        assert verify["digest_ok"] is True, verify
        assert verify["signature_ok"] is True, verify

    def test_blind_embed_512_still_capacity_400(self, client, db, auth_headers, adm2_headers, tmp_path):
        host = _make_geotiff(tmp_path / "host_512.tif", 512)
        item, _ = _seed_raster_app(db, host, "blind-compact-512")

        gen = client.post(
            "/api/generate_raster_watermark",
            json={"application_id": item.id, "reason": "compact on 512"},
            headers=auth_headers,
        )
        assert gen.status_code == 200, gen.get_data(as_text=True)
        qr_text = gen.get_json()["qr_text"]

        # Honest precondition: the compact payload itself overflows 512x512
        # (6,561 bits vs 4,095 embeddable) — the 400 below is the algorithm's
        # real boundary, not a dispatch artifact.
        side = _compact_qr_side(qr_text)
        assert side * side > 4096, f"compact QR {side}x{side} unexpectedly fits a 512x512 host"

        resp = client.post(
            "/api/embedding_watermark",
            json={"application_id": item.id, "algorithm": "blind"},
            headers=adm2_headers,
        )
        assert resp.status_code == 400, resp.get_data(as_text=True)
        msg = resp.get_json()["msg"]
        assert msg.startswith("Insufficient blind watermark capacity"), msg
        assert "1024" in msg, msg

    def test_blind_embed_legacy_row_without_qr_text_400(self, client, db, adm2_headers, tmp_path):
        from PIL import Image

        host = _make_geotiff(tmp_path / "host_1024_legacy.tif", 1024)
        item, _ = _seed_raster_app(db, host, "blind-legacy-noqrtext")
        # Legacy row: a display bitmap exists (small enough to fit), but the
        # QR text was never recorded — blind cannot rebuild its payload.
        buf = io.BytesIO()
        Image.new("L", (16, 16), 255).save(buf, format="PNG")
        item.qrcode = base64.b64encode(buf.getvalue()).decode()
        item.watermark_generated = True
        db.session.commit()

        resp = client.post(
            "/api/embedding_watermark",
            json={"application_id": item.id, "algorithm": "blind"},
            headers=adm2_headers,
        )
        # Pre-fix this legacy row embeds its small display bitmap and returns
        # the stego file (200); post-fix it must refuse with a 400 JSON body.
        assert resp.status_code == 400, f"expected 400, got {resp.status_code} ({resp.headers.get('Content-Type')})"
        assert resp.get_json()["msg"] == NO_QR_TEXT_MSG

    def test_embed_dispatch_backfills_qr_text_and_embeds_compact(self, client, db, adm2_headers, tmp_path):
        """CRMark path with no qrcode at all: the backfill
        (_create_qrcode_base64) must also record the QR text so the very same
        request's blind branch can rebuild the compact payload."""
        from model.Application import Application

        host = _make_geotiff(tmp_path / "host_1024_dispatch.tif", 1024)
        item, _ = _seed_raster_app(db, host, "blind-dispatch-backfill")
        assert item.qrcode is None  # nothing generated yet: the endpoint must backfill

        resp = client.post(
            "/api/admin/embed_dispatch",
            json={"application_id": item.id, "algorithm": "blind"},
            headers=adm2_headers,
        )
        assert resp.status_code == 200, resp.get_data(as_text=True)
        # The CRMark response (not the row) carries the meta path: that endpoint
        # persists only watermark_path on the application.
        meta_path = resp.get_json()["data"]["wm_meta_path"]

        db.session.expire_all()
        row = db.session.get(Application, item.id)
        assert row.qr_text  # persisted by the backfill alongside the bitmap
        assert row.watermark_embedded is True
        meta = _read_meta(meta_path)
        assert meta["algorithm"] == "blind_watermark"
        assert meta["watermark"]["bit_count"] < meta["capacity"]["block_num"]

    def test_embed_dispatch_blind_legacy_row_without_qr_text_400(self, client, db, adm2_headers, tmp_path):
        from PIL import Image

        host = _make_geotiff(tmp_path / "host_512_dispatch_legacy.tif", 512)
        item, _ = _seed_raster_app(db, host, "blind-dispatch-legacy")
        buf = io.BytesIO()
        Image.new("L", (16, 16), 255).save(buf, format="PNG")
        item.qrcode = base64.b64encode(buf.getvalue()).decode()
        item.watermark_generated = True
        db.session.commit()

        resp = client.post(
            "/api/admin/embed_dispatch",
            json={"application_id": item.id, "algorithm": "blind"},
            headers=adm2_headers,
        )
        assert resp.status_code == 400, resp.get_data(as_text=True)
        assert resp.get_json()["msg"] == NO_QR_TEXT_MSG
