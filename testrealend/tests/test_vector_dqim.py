"""D-QIM (scheme "dqim1") red/green gate: translation invariance for the vector chain.

E1 (red experiment, the reason this module exists): embed -> extract -> QR decode
-> COSE verify must succeed after a whole-map translation (+0.005, +0.003), while
the legacy absolute-coordinate scheme in the identical scenario must fail — the
two-sided evidence that the difference-domain carrier actually fixes the
translation weakness. E2 spot-checks noise (+/-1e-9 jitter) and 5% vertex
deletion on top of the translation; E3 checks capacity parity with the legacy
scheme for the same QR. Extraction dispatch (legacy vs "dqim1") is unit-tested
here; the end-to-end dispatch is covered by test_delivery_flow / forensics.
"""

import hashlib
import io
import math
import os
import zipfile
from datetime import UTC, datetime

import numpy as np
import pytest
from PIL import Image

from algorithm.embed import embed as legacy_embed
from algorithm.extract import extract as legacy_extract
from algorithm.vector_dqim import SCHEME, embed_dqim, extract_dqim
from crypto.keys import ensure_active_key
from crypto.payload import build_qr_v2_text, parse_qr_text
from delivery.qr2 import render_v2_qr_png
from resource.watermark_utils import decode_qr_from_image

E1_FID_HEX = "ab" * 16
E1_DELIVERY_ID = 4242


def _make_shp(path, n_lines=60, n_pts=300, x0=116.0, y0=39.0, seed=7):
    """Random-walk lines: n_lines x n_pts vertices (default 18000, like the delivery flow)."""
    import geopandas as gpd
    from shapely.geometry import LineString

    rng = np.random.default_rng(seed)
    lines = []
    for i in range(n_lines):
        xs = x0 + i * 0.01 + np.cumsum(rng.uniform(-0.001, 0.001, n_pts))
        ys = y0 + i * 0.01 + np.cumsum(rng.uniform(-0.001, 0.001, n_pts))
        lines.append(LineString(np.column_stack([xs, ys])))
    path = str(path)
    gpd.GeoDataFrame({"fid": range(n_lines)}, geometry=lines, crs="EPSG:4326").to_file(path)
    return path


def _translate_shp(src, dst, dx=0.005, dy=0.003):
    """Whole-map translation applied the way a user tool would: shapely affine on doubles."""
    import geopandas as gpd
    from shapely.affinity import translate

    gdf = gpd.read_file(src)
    gdf.geometry = gdf.geometry.apply(lambda g: translate(g, xoff=dx, yoff=dy))
    gdf.to_file(str(dst))
    return str(dst)


def _jitter_shp(src, dst, amplitude=1e-9, seed=11):
    """Coordinate jitter: uniform +/-amplitude, the E2 noise scenario."""
    import geopandas as gpd
    from shapely.geometry import LineString

    rng = np.random.default_rng(seed)
    gdf = gpd.read_file(src)
    new_geoms = []
    for geom in gdf.geometry:
        coords = np.array(geom.coords, dtype=float)
        coords = coords + rng.uniform(-amplitude, amplitude, coords.shape)
        new_geoms.append(LineString(coords))
    gdf.geometry = new_geoms
    gdf.to_file(str(dst))
    return str(dst)


def _delete_vertices_shp(src, dst, keep_mod=20):
    """Simplify-like attack: drop every keep_mod-th vertex of each line (5% for 20)."""
    import geopandas as gpd
    from shapely.geometry import LineString

    gdf = gpd.read_file(src)
    new_geoms = []
    for geom in gdf.geometry:
        coords = np.array(geom.coords, dtype=float)
        keep = np.arange(len(coords)) % keep_mod != 0
        coords = coords[keep]
        new_geoms.append(LineString(coords) if len(coords) >= 2 else geom)
    gdf.geometry = new_geoms
    gdf.to_file(str(dst))
    return str(dst)


def _unzip_first_shp(zip_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(out_dir)
    for name in sorted(os.listdir(out_dir)):
        if name.lower().endswith(".shp"):
            return os.path.join(out_dir, name)
    raise AssertionError("no .shp in artifact zip")


def _build_v2_qr(tmp_path):
    """The real delivery chain payload: COSE_Sign1 v2 text -> box_size=2 PNG."""
    kid, _private_key = ensure_active_key()
    text = build_qr_v2_text(E1_FID_HEX, E1_DELIVERY_ID, kid, int(datetime.now(UTC).timestamp()))
    png_path = str(tmp_path / "qr_v2.png")
    _, side = render_v2_qr_png(text, png_path)
    return text, png_path, side


def _pixel_agreement(qr_path, wm_path):
    """Payload agreement (BER complement) between original QR and rebuilt watermark, corners masked."""
    orig = np.array(Image.open(qr_path).convert("L")) > 127
    rec = np.array(Image.open(wm_path).convert("L")) > 127
    if orig.shape != rec.shape:
        return 0.0, 1.0
    mask = np.ones_like(orig, dtype=bool)
    mask[:8, :8] = mask[:8, -8:] = mask[-8:, :8] = False
    agreement = float((orig[mask] == rec[mask]).mean())
    return agreement, 1.0 - agreement


def _extract_wm_text(shp_path, vr, side_length, tmp_path, tag):
    _, wm_path = extract_dqim(shp_path, vr, side_length=side_length, output_dir=str(tmp_path / f"x_{tag}"))
    return decode_qr_from_image(wm_path), wm_path


class TestE1TranslationInvariance:
    """E1: the core red experiment — new scheme survives translation, legacy does not."""

    def test_e1_new_scheme_translated_and_legacy_fails(self, db, tmp_path):
        shp = _make_shp(tmp_path / "e1.shp")
        qr_text, qr_path, _ = _build_v2_qr(tmp_path)

        # ---------- new scheme (dqim1): baseline, then after translation ----------
        res = embed_dqim(shp, qr_path, output_dir=str(tmp_path / "emb_dqim"))
        assert res["scheme"] == SCHEME
        wshp = _unzip_first_shp(res["zip_path"], str(tmp_path / "unz_dqim"))

        text0, _ = _extract_wm_text(wshp, res["vr"], res["side_length"], tmp_path, "dqim0")
        print("E1 dqim baseline :", text0)
        assert text0 == qr_text, "D-QIM roundtrip failed before any attack"

        tshp = _translate_shp(wshp, tmp_path / "e1_translated.shp")
        text1, _ = _extract_wm_text(tshp, res["vr"], res["side_length"], tmp_path, "dqim1")
        print("E1 dqim translated:", text1)
        assert text1 == qr_text, "D-QIM must still extract after whole-map translation"
        parsed = parse_qr_text(text1)  # COSE_Sign1 verify against the key registry
        assert parsed["fid_hex"] == E1_FID_HEX
        assert parsed["delivery"] == E1_DELIVERY_ID

        # ---------- legacy control: works at baseline, must fail after translation ----------
        res_legacy = legacy_embed(shp, qr_path, output_dir=str(tmp_path / "emb_legacy"))
        wshp_legacy = _unzip_first_shp(res_legacy["zip_path"], str(tmp_path / "unz_legacy"))

        _, wm_l0 = legacy_extract(
            wshp_legacy,
            res_legacy["vr"],
            side_length=res_legacy["side_length"],
            output_dir=str(tmp_path / "xl0"),
        )
        text_l0 = decode_qr_from_image(wm_l0)
        print("E1 legacy baseline :", text_l0)
        assert text_l0 == qr_text, "legacy control must decode before translation, else the control is meaningless"

        tshp_legacy = _translate_shp(wshp_legacy, tmp_path / "e1_translated_legacy.shp")
        _, wm_l1 = legacy_extract(
            tshp_legacy,
            res_legacy["vr"],
            side_length=res_legacy["side_length"],
            output_dir=str(tmp_path / "xl1"),
        )
        text_l1 = decode_qr_from_image(wm_l1)
        print("E1 legacy translated:", text_l1)
        assert text_l1 != qr_text, "legacy scheme unexpectedly survived translation — E1 control broken"


class TestE2RobustnessSpotChecks:
    """E2: translation plus noise / vertex deletion — report actual BER, decode is the gate."""

    def test_e2_translation_with_jitter_and_deletion(self, db, tmp_path):
        # 100 x 400 = 40000 vertices -> lambda ~9.5 votes per chunk, so the
        # per-vote error rate of +/-1e-9 jitter (w-read ~10%, seed anchor flip
        # ~2-4%) stays far from the majority-vote cliff.
        shp = _make_shp(tmp_path / "e2.shp", n_lines=100, n_pts=400)
        qr_text, qr_path, _ = _build_v2_qr(tmp_path)
        res = embed_dqim(shp, qr_path, output_dir=str(tmp_path / "emb"))
        wshp = _unzip_first_shp(res["zip_path"], str(tmp_path / "unz"))

        translated = _translate_shp(wshp, tmp_path / "e2_translated.shp")

        # -- translation + +/-1e-9 jitter --
        jittered = _jitter_shp(translated, tmp_path / "e2_jittered.shp")
        text_j, wm_j = _extract_wm_text(jittered, res["vr"], res["side_length"], tmp_path, "jit")
        agree_j, ber_j = _pixel_agreement(qr_path, wm_j)
        print(f"E2 translated+jitter  decode={text_j!r} pixel_agreement={agree_j:.4f} BER={ber_j:.4f}")
        assert text_j == qr_text, f"D-QIM lost to 1e-9 jitter (BER={ber_j:.4f})"

        # -- translation + 5% vertex deletion --
        deleted = _delete_vertices_shp(translated, tmp_path / "e2_deleted.shp")
        text_d, wm_d = _extract_wm_text(deleted, res["vr"], res["side_length"], tmp_path, "del")
        agree_d, ber_d = _pixel_agreement(qr_path, wm_d)
        print(f"E2 translated+5%del  decode={text_d!r} pixel_agreement={agree_d:.4f} BER={ber_d:.4f}")
        assert text_d == qr_text, f"D-QIM lost to 5% vertex deletion (BER={ber_d:.4f})"


class TestE3CapacityParity:
    """E3: for the same QR, needed chunks must match the legacy scheme's demand."""

    def test_e3_needed_chunks_match_legacy(self, db, tmp_path):
        shp = _make_shp(tmp_path / "e3.shp", n_lines=30, n_pts=200)
        _qr_text, qr_path, side = _build_v2_qr(tmp_path)

        res_dqim = embed_dqim(shp, qr_path, output_dir=str(tmp_path / "emb_dqim"))
        res_legacy = legacy_embed(shp, qr_path, output_dir=str(tmp_path / "emb_legacy"))

        cap = res_dqim["capacity_report"]
        cap_legacy = res_legacy["capacity_report"]
        expected_needed = math.ceil((side**2 - 192) / 4)

        print("E3 dqim   cap:", cap)
        print("E3 legacy cap:", cap_legacy)
        assert cap["needed_chunks"] == expected_needed
        assert cap["needed_chunks"] == cap_legacy["needed_chunks"], "same QR must cost the same chunks"
        assert cap["available_chunks"] == cap["eligible_edges"]
        assert cap["eligible_edges"] <= cap["total_vertices"]
        assert res_dqim["side_length"] == side


class TestSchemeDispatch:
    """Legacy vr_data (no scheme key) must keep the legacy extractor; 'dqim1' the new one."""

    def test_dispatch_helper_selects_extractor(self):
        from algorithm.extract import extract
        from algorithm.vector_dqim import extract_dqim
        from resource.forensics_resource import _vector_extractor_for

        assert _vector_extractor_for({"vr": [1.0, 2.0], "side_length": 45}) is extract
        assert _vector_extractor_for({"scheme": "dqim1", "vr": [1.0, 2.0], "side_length": 130}) is extract_dqim
        assert _vector_extractor_for({"scheme": "unknown", "vr": [1.0, 2.0]}) is extract
