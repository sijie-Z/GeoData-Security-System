"""Tests for the IW-DCT raster scheme (feat_lab_iw, Track B).

Algorithm: ``algorithm/raster_iw_dct.py`` — one level of Haar DWT over the Y
channel, the LL subband cut into 4x4 blocks (iw's ``block=4`` geometry), one
payload bit per block carried by the order of a fixed mid-frequency DCT
coefficient pair ((1,2) vs (2,1)); the payload is repeated cyclically across
the block grid with per-bit majority voting (the iw ``num % wmLen`` design).

Bottom line pinned here (measured, not polished):
- no-attack embed -> extract is EXACT (bit-for-bit, NC == 1.0) on the
  standard 512x512 host with the standard payload QR;
- capacity shortfall -> ValueError whose message carries the need-vs-available
  numbers (and the full API path maps it to HTTP 400, same convention as the
  other raster schemes);
- GeoTIFF CRS is preserved; the embed is deterministic (same bytes);
- the scheme is registered in the engine (``RASTER_SCHEMES``) and a matrix
  smoke run produces a row for it.
"""

import json
import os

import numpy as np
import pytest

from algorithm.robustness_raster import (
    RASTER_SCHEMES,
    make_host_tif,
    r_resize,
    render_raster_payload_qr,
    run_raster_matrix,
)


def _build_matrix_payload():
    """Real v2 signed payload text (same construction as test_robustness)."""
    from datetime import UTC, datetime

    from crypto.keys import ensure_active_key
    from crypto.payload import build_qr_v2_text

    kid, _private_key = ensure_active_key()
    return build_qr_v2_text("ef" * 16, 4242, kid, int(datetime.now(UTC).timestamp()))


def _read_meta(path):
    with open(path, encoding="utf-8") as fp:
        return json.load(fp)


class TestIwDctRoundtrip:
    def test_no_attack_extraction_is_exact(self, db, tmp_path):
        """Embed -> blind extract must restore the payload bit-for-bit (NC == 1)."""
        from PIL import Image

        from algorithm.raster_iw_dct import embed_iw_dct, extract_iw_dct
        from resource.watermark_utils import decode_qr_from_image

        text = _build_matrix_payload()
        qr_path, side = render_raster_payload_qr(text, str(tmp_path / "payload_qr.png"))
        host = make_host_tif(str(tmp_path / "host.tif"))

        result = embed_iw_dct(host, Image.open(qr_path), str(tmp_path / "embed"), prefix="iwt")
        meta = _read_meta(result["wm_meta_path"])
        assert meta["algorithm"] == "iw_dct"
        assert meta["block_size"] == 4
        assert meta["capacity"]["block_num"] == 4096  # 512x512 -> (H//8)*(W//8)
        assert result["bit_count"] == side * side <= 4096

        out_png = extract_iw_dct(result["stego_path"], result["wm_meta_path"], str(tmp_path / "ext.png"))
        gt_bits = np.asarray(Image.open(qr_path).convert("L")) > 127
        ex_bits = np.asarray(Image.open(out_png).convert("L")) > 127
        assert ex_bits.shape == gt_bits.shape
        assert np.array_equal(gt_bits, ex_bits), "no-attack extraction must be bit-exact"
        assert decode_qr_from_image(out_png) == text

    def test_embed_is_deterministic(self, db, tmp_path):
        """Same input -> identical stego bytes (pure function, no RNG)."""
        from PIL import Image

        from algorithm.raster_iw_dct import embed_iw_dct

        text = _build_matrix_payload()
        qr_path, _side = render_raster_payload_qr(text, str(tmp_path / "payload_qr.png"))
        host = make_host_tif(str(tmp_path / "host.tif"))

        r1 = embed_iw_dct(host, Image.open(qr_path), str(tmp_path / "d1"), prefix="iwt")
        r2 = embed_iw_dct(host, Image.open(qr_path), str(tmp_path / "d2"), prefix="iwt")
        with open(r1["stego_path"], "rb") as f1, open(r2["stego_path"], "rb") as f2:
            assert f1.read() == f2.read()

    def test_geotiff_crs_is_preserved(self, db, tmp_path):
        import rasterio
        from PIL import Image

        from algorithm.raster_iw_dct import embed_iw_dct

        text = _build_matrix_payload()
        qr_path, _side = render_raster_payload_qr(text, str(tmp_path / "payload_qr.png"))
        host = make_host_tif(str(tmp_path / "host.tif"))

        result = embed_iw_dct(host, Image.open(qr_path), str(tmp_path / "crs"), prefix="iwt")
        assert result["stego_path"].endswith(".tif")
        with rasterio.open(result["stego_path"]) as src:
            assert src.crs is not None and src.crs.to_epsg() == 4326
            assert src.width == 512 and src.height == 512
        meta = _read_meta(result["wm_meta_path"])
        assert meta["geotiff"] is True

    def test_extraction_rejects_shrunk_geometry_honestly(self, db, tmp_path):
        """A 0.5x resize keeps only 1024 blocks (< payload bits): the extractor
        must refuse with an explicit error instead of returning garbage."""
        from PIL import Image

        from algorithm.raster_iw_dct import embed_iw_dct, extract_iw_dct

        text = _build_matrix_payload()
        qr_path, _side = render_raster_payload_qr(text, str(tmp_path / "payload_qr.png"))
        host = make_host_tif(str(tmp_path / "host.tif"))

        result = embed_iw_dct(host, Image.open(qr_path), str(tmp_path / "embed"), prefix="iwt")
        attacked = r_resize(result["stego_path"], factor=0.5, output_path=str(tmp_path / "small.tif"))
        with pytest.raises(ValueError, match="too small for IW-DCT extraction"):
            extract_iw_dct(attacked, result["wm_meta_path"], str(tmp_path / "ext.png"))


class TestIwDctCapacity:
    def test_capacity_error_message_has_numbers(self, db, tmp_path):
        from PIL import Image

        from algorithm.raster_iw_dct import embed_iw_dct

        text = _build_matrix_payload()
        qr_path, side = render_raster_payload_qr(text, str(tmp_path / "payload_qr.png"))
        host = make_host_tif(str(tmp_path / "host256.tif"), size=256)

        with pytest.raises(ValueError) as excinfo:
            embed_iw_dct(host, Image.open(qr_path), str(tmp_path / "embed"), prefix="iwt")
        msg = str(excinfo.value)
        assert msg.startswith("Insufficient IW-DCT capacity"), msg
        assert str(side * side) in msg  # need N blocks
        assert "1024" in msg  # the 256x256 host provides only 1024 blocks

    def test_api_capacity_shortfall_is_400_with_numbers(self, client, db, auth_headers, adm2_headers, tmp_path):
        """The full API path on a 512x512 host: compact payload overflows the
        4096-block budget -> 400 with the numbers."""
        from tests.test_blind_compact import _compact_qr_side, _make_geotiff, _seed_raster_app

        host = _make_geotiff(tmp_path / "host_512.tif", 512)
        item, _ = _seed_raster_app(db, host, "iwdct-512")

        gen = client.post(
            "/api/generate_raster_watermark",
            json={"application_id": item.id, "reason": "iw_dct capacity"},
            headers=auth_headers,
        )
        assert gen.status_code == 200, gen.get_data(as_text=True)
        qr_text = gen.get_json()["qr_text"]

        # Honest precondition: the compact payload itself overflows 512x512
        # (the 400 below is the algorithm's real boundary, not a dispatch artifact).
        side = _compact_qr_side(qr_text)
        assert side * side > 4096, f"compact QR {side}x{side} unexpectedly fits a 512x512 host"

        resp = client.post(
            "/api/embedding_watermark",
            json={"application_id": item.id, "algorithm": "iw_dct"},
            headers=adm2_headers,
        )
        assert resp.status_code == 400, resp.get_data(as_text=True)
        msg = resp.get_json()["msg"]
        assert msg.startswith("Insufficient IW-DCT capacity"), msg
        assert str(side * side) in msg and "4096" in msg, msg

    def test_api_1024_roundtrip_through_extract_endpoint(
        self, client, db, auth_headers, adm2_headers, adm3_headers, tmp_path
    ):
        """1024x1024 host: compact payload fits (16384 blocks) -> 200, meta is
        iw_dct, and the extract endpoint's iw_dct dispatch recovers the signed
        QR text (digest + signature verify)."""
        from tests.test_blind_compact import _compact_qr_side, _make_geotiff, _seed_raster_app

        host = _make_geotiff(tmp_path / "host_1024.tif", 1024)
        item, _ = _seed_raster_app(db, host, "iwdct-1024")

        gen = client.post(
            "/api/generate_raster_watermark",
            json={"application_id": item.id, "reason": "iw_dct roundtrip"},
            headers=auth_headers,
        )
        assert gen.status_code == 200, gen.get_data(as_text=True)
        qr_text = gen.get_json()["qr_text"]

        resp = client.post(
            "/api/embedding_watermark",
            json={"application_id": item.id, "algorithm": "iw_dct"},
            headers=adm2_headers,
        )
        assert resp.status_code == 200, resp.get_data(as_text=True)

        from model.Application import Application

        db.session.expire_all()
        row = db.session.get(Application, item.id)
        stego, meta_path = row.watermark_path, row.watermark_path_meta
        assert stego and os.path.isfile(stego), stego
        meta = _read_meta(meta_path)
        assert meta["algorithm"] == "iw_dct"
        assert meta["capacity"]["block_num"] == 16384
        assert meta["watermark"]["width"] == _compact_qr_side(qr_text)

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


class TestIwDctEngineRegistration:
    def test_scheme_is_registered(self):
        assert "iw_dct" in RASTER_SCHEMES

    def test_matrix_smoke_row_for_iw_dct(self, db, tmp_path):
        """A matrix run over the new scheme produces a successful baseline row."""
        text = _build_matrix_payload()
        qr_path, _side = render_raster_payload_qr(text, str(tmp_path / "payload_qr.png"))
        host = make_host_tif(str(tmp_path / "host.tif"))

        rows = run_raster_matrix(host, ["iw_dct"], ["none"], qr_path, str(tmp_path / "work"))
        assert len(rows) == 1
        row = rows[0]
        assert (row["scheme"], row["attack"]) == ("iw_dct", "none")
        assert row["decode_success"] is True, f"iw_dct baseline lost: {row}"
        # Exactness: BER == 0 proves bit-for-bit equality; NC sits within float
        # rounding of 1.0 (the cosine is evaluated as dot/(norm*norm) in float64,
        # so identical bit arrays can land ~1e-16 below 1.0 — not a bit error).
        assert row["ber"] == 0.0, f"iw_dct baseline not bit-exact: {row}"
        assert row["nc"] is not None and row["nc"] > 1.0 - 1e-9, f"iw_dct baseline NC too low: {row}"
        assert row["duration_ms"] is not None and row["duration_ms"] >= 0
