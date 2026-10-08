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
    r_crop,
    r_jpeg,
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


def _render_compact_payload(text, path):
    """Render a short payload at the matrix contract (box_size=1, ECC L, border 4).

    The standard v2 payload renders 57x57 px — 3,249 bits on the 512-host's
    4,096 blocks, ~79% utilization, i.e. only ~1.26 votes per bit — so a center
    crop that removes a column band of blocks leaves hundreds of payload bits
    with no surviving vote at all: beyond the QR's error correction and
    unrecoverable without the host template. Crop recovery needs the
    lower-utilization regime the blind module documents (keep ``wm_bits`` well
    below ``block_num``); this compact payload renders 41x41 px (1,681 bits,
    ~2.4 votes/bit), the size the crop-realignment tests are built on.
    Returns ``(png_path, side)``.
    """
    import qrcode

    from delivery.qr2 import render_v2_qr_png

    return render_v2_qr_png(text, path, box_size=1, error_correction=qrcode.constants.ERROR_CORRECT_L)


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

    def test_sweep_smoke_rows_for_iw_dct(self, db, tmp_path):
        """Strength-sweep mode covers the new scheme automatically — the sweep
        runner expands every requested attack into the 5 ladder tiers and pulls
        embed/extract from the same scheme dispatch as the matrix."""
        from algorithm.robustness_raster import run_raster_sweep
        from algorithm.robustness_sweep import SWEEP_TIER_COUNT

        text = _build_matrix_payload()
        qr_path, _side = render_raster_payload_qr(text, str(tmp_path / "payload_qr.png"))
        host = make_host_tif(str(tmp_path / "host.tif"))

        rows = run_raster_sweep(host, ["iw_dct"], ["jpeg"], qr_path, str(tmp_path / "work_sweep"), trials=1)
        assert len(rows) == SWEEP_TIER_COUNT
        assert {r["strength_index"] for r in rows} == set(range(SWEEP_TIER_COUNT))
        assert all(r["scheme"] == "iw_dct" and r["attack"] == "jpeg" for r in rows)
        assert all(r["decode_success"] is not None for r in rows)


class TestIwDctCropRealignment:
    """Center-crop recovery for IW-DCT (feat_iw_align).

    Red evidence, captured on the pre-realignment extractor (same fixtures):
    every crop tier below decoded to ``None`` — a center crop shifts the block
    grid phase and re-indexes the flat payload, so the naive readout is noise.
    The realignment search (block-grid phase x cyclic flat-offset, scored by
    the QR's own structure: finders / timing / border / dark module) turns the
    90% and 80% tiers green at the compact payload's ~2.4 votes/bit, while the
    standard 57 px payload at ~1.26 votes/bit stays an honest failure (missing
    votes exceed the QR error-correction budget — no blind scheme can recover
    those bits without the host template; the blind module documents the same
    utilization rule).
    """

    COMPACT_TEXT = "iw-dct-crop-realign-payload-31f5a2c8d4e6b7a9c1d2e3f4a5b6c7"
    COMPACT_SIDE = 41  # v4 QR (33 modules) + 4-module border, box_size=1

    def _embed_compact(self, tmp_path):
        from PIL import Image

        from algorithm.raster_iw_dct import embed_iw_dct

        qr_path, side = _render_compact_payload(self.COMPACT_TEXT, str(tmp_path / "compact_qr.png"))
        assert side == self.COMPACT_SIDE, f"compact payload precondition changed: side={side}"
        host = make_host_tif(str(tmp_path / "host.tif"))
        result = embed_iw_dct(host, Image.open(qr_path), str(tmp_path / "embed"), prefix="iwc")
        return result

    def test_center_crop_90_80_decode_and_65_stays_honest(self, db, tmp_path):
        from algorithm.raster_iw_dct import extract_iw_dct
        from resource.watermark_utils import decode_qr_from_image

        result = self._embed_compact(tmp_path)
        assert result["bit_count"] == self.COMPACT_SIDE**2

        for keep in (0.9, 0.8):
            attacked = r_crop(result["stego_path"], keep=keep, output_path=str(tmp_path / f"crop_{keep}.tif"))
            out_png = extract_iw_dct(attacked, result["wm_meta_path"], str(tmp_path / f"ext_{keep}.png"))
            decoded = decode_qr_from_image(out_png)
            assert decoded == self.COMPACT_TEXT, f"crop keep={keep} not recovered: {decoded!r}"

        # Determinism: the realignment is a pure function (no RNG) — two
        # extractions of the same cropped stego must be byte-identical.
        attacked = r_crop(result["stego_path"], keep=0.9, output_path=str(tmp_path / "crop_det.tif"))
        out_a = extract_iw_dct(attacked, result["wm_meta_path"], str(tmp_path / "ext_a.png"))
        out_b = extract_iw_dct(attacked, result["wm_meta_path"], str(tmp_path / "ext_b.png"))
        with open(out_a, "rb") as fa, open(out_b, "rb") as fb:
            assert fa.read() == fb.read()

        # keep=0.65 removes enough block bands that a large share of payload
        # bits has no surviving vote at all — beyond the QR error correction.
        # The extractor must fail honestly: no crash, no fake recovery.
        attacked65 = r_crop(result["stego_path"], keep=0.65, output_path=str(tmp_path / "crop_65.tif"))
        out65 = extract_iw_dct(attacked65, result["wm_meta_path"], str(tmp_path / "ext_65.png"))
        assert decode_qr_from_image(out65) != self.COMPACT_TEXT

    def test_standard_payload_crop_stays_an_honest_failure(self, db, tmp_path):
        """The standard 57 px matrix payload is at ~79% utilization (~1.26
        votes per bit): a keep=0.9 center crop leaves ~370 payload bits with
        zero surviving votes — far beyond the QR error correction. The
        extractor returns its best structured readout (no crash, no fake
        recovery); keep=0.8 shrinks the naive grid below the payload and still
        refuses with the capacity error, unchanged."""
        from PIL import Image

        from algorithm.raster_iw_dct import embed_iw_dct, extract_iw_dct
        from resource.watermark_utils import decode_qr_from_image

        text = _build_matrix_payload()
        qr_path, side = render_raster_payload_qr(text, str(tmp_path / "payload_qr.png"))
        host = make_host_tif(str(tmp_path / "host.tif"))
        result = embed_iw_dct(host, Image.open(qr_path), str(tmp_path / "embed"), prefix="iws")
        assert result["bit_count"] == side * side

        attacked = r_crop(result["stego_path"], keep=0.9, output_path=str(tmp_path / "crop_90.tif"))
        out_png = extract_iw_dct(attacked, result["wm_meta_path"], str(tmp_path / "ext_90.png"))
        assert decode_qr_from_image(out_png) != text

        attacked80 = r_crop(result["stego_path"], keep=0.8, output_path=str(tmp_path / "crop_80.tif"))
        with pytest.raises(ValueError, match="too small for IW-DCT extraction"):
            extract_iw_dct(attacked80, result["wm_meta_path"], str(tmp_path / "ext_80.png"))

    def test_realignment_search_only_runs_on_failed_fast_path(self, db, tmp_path, monkeypatch):
        """The realignment search is a failure-path fallback: clean and
        compression/noise extractions take the fast path (the search must not
        even be called — this is what keeps the no-attack timing flat), while a
        center crop that scrambles the naive grid triggers it."""
        import algorithm.raster_iw_dct as mod
        from resource.watermark_utils import decode_qr_from_image

        result = self._embed_compact(tmp_path)
        calls = {"n": 0}
        original = mod._realign_search

        def spy(*args, **kwargs):
            calls["n"] += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(mod, "_realign_search", spy)

        out = mod.extract_iw_dct(result["stego_path"], result["wm_meta_path"], str(tmp_path / "e_none.png"))
        assert decode_qr_from_image(out) == self.COMPACT_TEXT
        assert calls["n"] == 0, "no-attack extraction must stay on the fast path"

        jpeg = r_jpeg(result["stego_path"], quality=70, output_path=str(tmp_path / "jpeg70.tif"))
        out = mod.extract_iw_dct(jpeg, result["wm_meta_path"], str(tmp_path / "e_jpeg.png"))
        assert decode_qr_from_image(out) == self.COMPACT_TEXT
        assert calls["n"] == 0, "compression-only attack must stay on the fast path"

        crop = r_crop(result["stego_path"], keep=0.9, output_path=str(tmp_path / "crop.tif"))
        out = mod.extract_iw_dct(crop, result["wm_meta_path"], str(tmp_path / "e_crop.png"))
        assert decode_qr_from_image(out) == self.COMPACT_TEXT
        assert calls["n"] >= 1, "a grid-scrambling crop must trigger the realignment search"

    def test_no_attack_extraction_overhead_below_10_percent(self, db, tmp_path):
        """无攻击路径耗时不得劣化 >10%: the gate is one O(n log n) structure
        score on the already-computed votes (~14 us measured). Both variants
        are timed interleaved in one process against the same stego, so slow
        machine drift cancels and the ratio is machine-independent."""
        import statistics
        import time

        import algorithm.raster_iw_dct as mod
        from resource.watermark_utils import decode_qr_from_image

        result = self._embed_compact(tmp_path)
        real_score = mod._structure_score
        no_gate = lambda *a, **k: float("inf")  # short-circuit stand-in for the gate

        mod.extract_iw_dct(result["stego_path"], result["wm_meta_path"], str(tmp_path / "warm.png"))  # warm-up
        full_times, short_times = [], []
        short_png = None
        try:
            for i in range(6):
                t0 = time.perf_counter()
                mod.extract_iw_dct(result["stego_path"], result["wm_meta_path"], str(tmp_path / f"full_{i}.png"))
                full_times.append(time.perf_counter() - t0)
                mod._structure_score = no_gate
                t0 = time.perf_counter()
                short_png = mod.extract_iw_dct(
                    result["stego_path"], result["wm_meta_path"], str(tmp_path / f"short_{i}.png")
                )
                short_times.append(time.perf_counter() - t0)
                mod._structure_score = real_score
        finally:
            mod._structure_score = real_score

        assert decode_qr_from_image(short_png) == self.COMPACT_TEXT  # short-circuit still extracts
        t_full = statistics.median(full_times)
        t_short = statistics.median(short_times)
        overhead = (t_full - t_short) / t_full
        assert overhead < 0.10, (
            f"fast-path overhead {overhead:.1%} exceeds the 10% budget (full {t_full * 1000:.1f} ms)"
        )

    def test_matrix_crop_row_turns_green_for_compact_payload(self, db, tmp_path, monkeypatch):
        """Engine-level: with the matrix crop default set to keep=0.9, the
        iw_dct crop row decodes the compact payload end to end through
        run_raster_matrix (red before the realignment: decode_success False)."""
        from algorithm import robustness_raster

        monkeypatch.setitem(robustness_raster.RASTER_ATTACK_DEFAULTS, "crop", {"keep": 0.9})
        qr_path, side = _render_compact_payload(self.COMPACT_TEXT, str(tmp_path / "compact_qr.png"))
        assert side == self.COMPACT_SIDE
        host = make_host_tif(str(tmp_path / "host.tif"))

        rows = run_raster_matrix(host, ["iw_dct"], ["none", "crop"], qr_path, str(tmp_path / "work_crop"))
        by_attack = {r["attack"]: r for r in rows}
        assert by_attack["none"]["decode_success"] is True
        assert by_attack["crop"]["decode_success"] is True, f"crop row still red: {by_attack['crop']}"
