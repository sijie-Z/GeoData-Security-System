"""Tests for the blind (DWT-DCT-SVD) raster watermark algorithm.

The fourth raster algorithm (blind_watermark 0.4.4): payload bits are
embedded one per 8x8 pixel block with SVD-modulated DCT coefficients and
recovered blind (password + watermark dimensions only, no change map).

Reference numbers measured on this machine with the installed library (the
algorithm is deterministic), used to pick the assertion thresholds:

- Uncropped roundtrip on a 512x512 GeoTIFF: exact bitmap recovery
  (NC 1.0, PSNR ~37.8 dB).
- 30% center crop of a 1024x1024 stego holding a 41x41 watermark (10.3%
  block utilization), with the original host as the realignment template
  (recorded as host_path in the meta; library recipe
  ``estimate_crop_parameters`` + ``recover_crop``): NC 1.0 (threshold 0.9).
- The same crop extracted WITHOUT the template is noise (NC ~0.57) — a
  documented limit, not asserted here: crop recovery needs the original.
- Crops that keep the image width and the top-left origin (e.g. trimming
  bottom rows) decode with NC 1.0 and need no template at all.
- Capacity limit: one bit per 8x8 block, strictly less than
  floor(((H+1)//2)/4) * floor(((W+1)//2)/4); a 512x512 host fits at most
  4095 bits (a 64x64 bitmap is already one bit too large).
"""

import base64
import hashlib
import hmac
import io
import json
import os
import shutil
from datetime import UTC, datetime

import numpy as np
import pytest
import qrcode
import rasterio
from rasterio.transform import from_bounds

FIXTURE_BOUNDS = (119.9, 29.9, 120.1, 30.1)


def _make_geotiff(path, size=512):
    """A real, georeferenced 3-band uint8 GeoTIFF (same shape as test_raster)."""
    rng = np.random.default_rng(7)
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


def _make_qr(size_px=41):
    """A real QR bitmap at the given pixel size (box_size=1 -> 41px is v4)."""
    qr = qrcode.QRCode(version=4, box_size=1, border=4, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data("BWM-TEST-PAYLOAD-0123456789-0123456789-0123456789")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("L")
    assert img.size == (size_px, size_px), img.size
    return img


def _qr_bits(img):
    return np.array(img.convert("L")) > 127


def _read_meta(path):
    with open(path, encoding="utf-8") as fp:
        return json.load(fp)


def _signed_qr_text(app_id, alias):
    """Compact payload following the build_qr_text convention (Signature last,
    same HMAC the extract endpoint verifies)."""
    from resource.watermark_utils import QR_SECRET_KEY

    content = "\n".join(
        [
            "=== SPATIAL DATA TRACKING SYSTEM ===",
            f"AppID: {app_id}",
            "DataType: raster",
            f"Data: {alias}",
        ]
    )
    sig = hmac.new(QR_SECRET_KEY.encode(), content.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{content}\nSignature: {sig}\n=== END ==="


def _build_qr_png_b64(text, box_size=1):
    """QR PNG at natural size; returns (base64, pixel side). box_size=1 keeps
    the bitmap within the blind algorithm's ~1 bit / 64 pixels capacity."""
    qr = qrcode.QRCode(box_size=box_size, border=4, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("L")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode(), img.size[0]


def _seed_raster_app(db, tif_path, alias="blind-host"):
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
        reason="blind watermark test",
        adm1_statu=True,
        adm2_statu=True,
    )
    db.session.add(item)
    db.session.commit()
    # Clear stale runtime artifacts so the extract endpoint's meta-file
    # discovery is deterministic (same pattern as test_raster).
    shutil.rmtree(os.path.join(current_app.root_path, "runtime", "crmark", f"app_{item.id}"), ignore_errors=True)
    return item, str(tif_path)


class TestBlindRoundtrip:
    def test_embed_extract_roundtrip_preserves_crs(self, tmp_path):
        from PIL import Image

        from algorithm.quality_metrics import compute_nc
        from algorithm.raster_blind_watermark import embed_blind, extract_blind

        host = _make_geotiff(tmp_path / "host.tif", 512)
        wm = _make_qr()
        res = embed_blind(host, wm, str(tmp_path / "out"), "app_1")
        assert os.path.isfile(res["stego_path"])
        assert os.path.isfile(res["wm_meta_path"])
        assert res["psnr"] > 30
        assert res["bit_count"] == wm.size[0] * wm.size[1]
        assert res["blocks"] == 4096  # (512//2//4)^2

        # The GeoTIFF write-back must keep CRS/transform (rasterio path).
        with rasterio.open(res["stego_path"]) as src:
            assert src.crs is not None and src.crs.to_epsg() == 4326
            assert src.transform == from_bounds(*FIXTURE_BOUNDS, 512, 512)
            assert src.count == 3

        out = str(tmp_path / "wm_out.png")
        extract_blind(res["stego_path"], res["wm_meta_path"], out)

        orig = _qr_bits(wm)
        rec = np.array(Image.open(out).convert("L")) > 127
        assert rec.shape == orig.shape
        agreement = float((orig == rec).mean())
        nc = compute_nc(orig.astype(float).reshape(-1), rec.astype(float).reshape(-1))
        # Measured: exact (agreement 1.0, NC 1.0).
        assert agreement >= 0.98, f"bit agreement {agreement:.4f}"
        assert nc >= 0.95, f"NC {nc:.4f}"

        meta = _read_meta(res["wm_meta_path"])
        assert meta["algorithm"] == "blind_watermark"
        assert meta["password_img"] == 1 and meta["password_wm"] == 1
        assert meta["watermark"]["height"] == wm.size[1]
        assert meta["watermark"]["width"] == wm.size[0]
        assert meta["geotiff"] is True


class TestBlindCropRecovery:
    """The blind algorithm's selling point. A center crop shifts the block
    grid, so extraction is realigned with the original host as template
    (library recipe; extract_blind does it automatically via the host_path
    recorded in the meta). Measured on a 1024x1024 host with a 41x41
    watermark (10.3% block utilization): NC 1.0 after a 30% crop. Without
    the template the same crop extracts noise (NC ~0.57, not asserted)."""

    def test_center_crop_30pct_recovers_with_template(self, tmp_path):
        from PIL import Image

        from algorithm.quality_metrics import compute_nc
        from algorithm.raster_blind_watermark import embed_blind, extract_blind

        host = _make_geotiff(tmp_path / "host_big.tif", 1024)
        wm = _make_qr()
        res = embed_blind(host, wm, str(tmp_path / "out"), "app_2")

        with rasterio.open(res["stego_path"]) as src:
            stego = np.moveaxis(src.read(), 0, -1)
        keep = int(1024 * 0.7)
        y0 = (1024 - keep) // 2
        crop_path = str(tmp_path / "crop30.png")
        Image.fromarray(stego[y0 : y0 + keep, y0 : y0 + keep], mode="RGB").save(crop_path)

        out = str(tmp_path / "wm_crop.png")
        extract_blind(crop_path, res["wm_meta_path"], out)

        orig = _qr_bits(wm)
        rec = np.array(Image.open(out).convert("L")) > 127
        nc = compute_nc(orig.astype(float).reshape(-1), rec.astype(float).reshape(-1))
        # Measured: NC 1.0 at this utilization (10.3%).
        assert nc >= 0.9, f"crop-recovered NC {nc:.4f}"

    def test_width_preserving_crop_recovers_without_template(self, tmp_path):
        from PIL import Image

        from algorithm.quality_metrics import compute_nc
        from algorithm.raster_blind_watermark import embed_blind, extract_blind

        host = _make_geotiff(tmp_path / "host_bottom.tif", 1024)
        wm = _make_qr()
        res = embed_blind(host, wm, str(tmp_path / "out"), "app_3")

        with rasterio.open(res["stego_path"]) as src:
            stego = np.moveaxis(src.read(), 0, -1)
        keep = int(1024 * 0.7)
        crop_path = str(tmp_path / "crop_bottom.png")
        Image.fromarray(stego[:keep, :], mode="RGB").save(crop_path)

        # Drop host_path from the meta: no template is available, this crop
        # class (width and origin preserved) must still decode directly.
        meta = _read_meta(res["wm_meta_path"])
        meta.pop("host_path")
        meta_no_host = str(tmp_path / "meta_no_host.json")
        with open(meta_no_host, "w", encoding="utf-8") as fp:
            json.dump(meta, fp)

        out = str(tmp_path / "wm_bottom.png")
        extract_blind(crop_path, meta_no_host, out)

        orig = _qr_bits(wm)
        rec = np.array(Image.open(out).convert("L")) > 127
        nc = compute_nc(orig.astype(float).reshape(-1), rec.astype(float).reshape(-1))
        # Measured: NC 1.0 (block grid and bit-to-block assignment preserved).
        assert nc >= 0.95, f"bottom-crop NC {nc:.4f}"


class TestBlindCapacity:
    def test_oversized_watermark_raises_insufficient(self, tmp_path):
        from PIL import Image

        from algorithm.raster_blind_watermark import embed_blind

        host = _make_geotiff(tmp_path / "host_cap.tif", 512)  # 4096 blocks -> max 4095 bits
        too_big = Image.new("L", (64, 64), 255)  # 4096 bits: one over the limit
        with pytest.raises(ValueError, match=r"Insufficient blind watermark capacity: need 4096 bits"):
            embed_blind(host, too_big, str(tmp_path / "out"), "app_cap")

    def test_endpoint_maps_capacity_error_to_400(self, client, db, adm2_headers, tmp_path):
        from PIL import Image

        from resource.watermark_utils import build_qr_text

        host = _make_geotiff(tmp_path / "host_cap_api.tif", 512)
        item, _ = _seed_raster_app(db, host, alias="blind-cap-host")

        buf = io.BytesIO()
        Image.new("L", (128, 128), 255).save(buf, format="PNG")
        item.qrcode = base64.b64encode(buf.getvalue()).decode()
        # Since the compact-QR fix the blind branch embeds a box_size=1
        # re-render of qr_text instead of this bitmap; the real generated text
        # is 81x81 px (6,561 bits) and still overflows the 512x512 host's
        # 4,095-bit budget, which keeps this capacity-mapping test meaningful.
        qr_text, _signature = build_qr_text(item, {"reason": item.reason})
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=1, border=4)
        qr.add_data(qr_text)
        qr.make(fit=True)
        side = qr.make_image().size[0]
        assert side * side > 4096, "test text must overflow the 512x512 host"
        item.qr_text = qr_text
        item.watermark_generated = True
        db.session.commit()

        resp = client.post(
            "/api/admin/embed_dispatch",
            json={"application_id": item.id, "algorithm": "blind"},
            headers=adm2_headers,
        )
        assert resp.status_code == 400, resp.get_data(as_text=True)
        msg = resp.get_json()["message"]
        assert msg.startswith("Insufficient blind watermark capacity"), msg


class TestBlindEndpoints:
    def test_embed_dispatch_then_decode_and_extract(self, client, db, adm2_headers, adm3_headers, tmp_path):
        from model.Application import Application

        host = _make_geotiff(tmp_path / "host_api.tif", 512)
        item, _ = _seed_raster_app(db, host, alias="blind-api-host")
        qr_text = _signed_qr_text(item.id, "blind-api-host")
        item.qrcode, side = _build_qr_png_b64(qr_text)
        # The blind branch now embeds the compact box_size=1 re-render of
        # qr_text (ECC L: 49x49 px / 2,401 bits here), not this bitmap.
        item.qr_text = qr_text
        item.watermark_generated = True
        db.session.commit()
        assert side * side < 4096, "test QR must fit the 512x512 host"

        resp = client.post(
            "/api/admin/embed_dispatch",
            json={"application_id": item.id, "algorithm": "blind"},
            headers=adm2_headers,
        )
        assert resp.status_code == 200, resp.get_json()
        data = resp.get_json()["data"]
        stego, meta = data["stego_path"], data["wm_meta_path"]
        assert stego.endswith(".tif")
        assert os.path.isfile(stego) and os.path.isfile(meta)
        with rasterio.open(stego) as src:
            assert src.crs is not None
        assert _read_meta(meta)["algorithm"] == "blind_watermark"

        db.session.expire_all()
        row = db.session.get(Application, item.id)
        assert row.watermark_embedded is True
        assert row.watermark_path == stego
        assert os.path.isfile(row.watermark_path)

        # CRMark decode endpoint dispatches on meta.algorithm.
        dec = client.post(
            "/api/crmark/decode",
            json={"stego_path": stego, "wm_meta_path": meta},
            headers=adm2_headers,
        )
        assert dec.status_code == 200, dec.get_data(as_text=True)
        assert dec.data[:8] == b"\x89PNG\r\n\x1a\n"

        # Upload extraction endpoint: the extracted bitmap must decode back to
        # the signed QR text (digest + HMAC verification).
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
