"""Robustness experiment matrix engine for the vector watermarking schemes.

This is the authoritative data source for the "experimental results" feature:
for every scheme (``legacy`` absolute-coordinate QIM in ``algorithm/embed.py``,
``dqim1`` difference-domain QIM in ``algorithm/vector_dqim.py``) the same QR
payload is embedded once, the no-attack baseline is measured first, then every
standard coordinate attack (translation / scaling / vertex deletion / Gaussian
noise / simplification) is applied to a copy of the stego shapefile and read
back with that scheme's extractor. One row per (scheme, attack, trial) carries:

  * ``decode_success`` — ``decode_qr_from_image`` returned exactly
    ``payload_text`` (the payload-level gate);
  * ``nc`` / ``ber`` — bit-level fidelity between the rebuilt watermark bitmap
    and the original payload QR bitmap (``quality_metrics.compute_nc`` /
    ``compute_ber`` on 0/1 bit sequences, the same reference convention as
    ``tests/benchmark_all_algorithms.py``). A QR that cannot be decoded at all
    yields ``decode_success=False`` with NC/BER ``None`` (nothing to compare);
  * ``trial`` — 1-based trial index of a multi-trial run;
  * ``attack_params`` — the parameters actually used for this cell. With
    ``trials > 1`` each trial samples the documented intervals with the fixed
    seed ``TRIAL_BASE_SEED + trial`` (see ``sample_trial_params``), so the whole
    matrix is bit-reproducible from the request alone; ``trials == 1`` keeps the
    documented ``ATTACK_DEFAULTS`` (the interval midpoints) for continuity with
    the pre-trials experiments;
  * ``duration_ms`` — wall time of the attack + extract + decode + metrics cell.

Discipline: everything here is a pure function of its arguments — no Flask
context (all embed/extract outputs go under the caller-provided ``work_dir``),
no DB, no globals. Persisting rows is the service layer's duty.
"""

import logging
import os
import time
import zipfile

import numpy as np

# The raster matrix engine (feat_raster_robustness) lives in its own module;
# re-exported here so both matrices have one import point. Nothing in this
# file's vector engine changes.
from algorithm.robustness_raster import (
    RASTER_ATTACK_DEFAULTS,
    RASTER_ATTACKS,
    RASTER_SCHEMES,
    make_host_tif,
    render_raster_payload_qr,
    run_raster_matrix,
)

# The two vector schemes the matrix compares. "legacy" artifacts carry no
# scheme marker; "dqim1" matches ``algorithm.vector_dqim.SCHEME``.
SCHEMES = ("legacy", "dqim1")

# Standard attack set (literature-consensus coordinate attacks + the no-attack
# baseline). "none" is always measured first so a broken control is obvious.
ATTACKS = ("none", "translate", "scale", "vertex_drop", "noise", "simplify")

# Default parameters per attack. "translate" defaults to the E1-measured lethal
# shift for the legacy scheme (+0.005, +0.003 degrees); "simplify" tolerance
# None means "auto" = bounding-box diagonal x 1e-4 (resolved per dataset).
ATTACK_DEFAULTS = {
    "none": {},
    "translate": {"dx": 0.005, "dy": 0.003},
    "scale": {"factor": 2.0},
    "vertex_drop": {"pct": 0.05},
    "noise": {"sigma": 1e-9},
    "simplify": {"tolerance": None},
}

# Fixed seed for the deterministic Gaussian-noise attack (E2 used seed 11);
# trial ``t`` (1-based) of a multi-trial run uses ``NOISE_SEED + t``.
NOISE_SEED = 11

# Multi-trial parameter sampling (feat_experiment_trials): with ``trials > 1``
# trial ``t`` draws every attack's parameters from the documented intervals
# below using ``np.random.default_rng(TRIAL_BASE_SEED + t)`` — a fixed seed,
# so the same request reproduces bit-identical rows. The interval midpoints
# equal the ``ATTACK_DEFAULTS``, which is what ``trials == 1`` keeps using.
TRIAL_BASE_SEED = 11

VECTOR_TRIAL_INTERVALS = {
    "translate": {"dx": (0.003, 0.008), "dy": (0.002, 0.005)},
    "scale": {"factor": (1.5, 3.0)},
    "vertex_drop": {"pct": (0.03, 0.08)},
    "noise": {"sigma": (5e-10, 2e-9)},
    "simplify": {"tolerance_multiplier": (0.5, 1.5)},
}


def sample_trial_params(trial):
    """Attack parameters for trial ``trial`` (1-based), fixed-seed sampled.

    Draws run over the full canonical ``ATTACKS`` order (not just the requested
    subset), so a trial's parameters are a property of the trial itself —
    identical whether a caller requests every attack or a subset — and both
    schemes of a run see the same attack conditions per trial (paired design).
    ``none`` is not jittered (empty params, recorded as-is). ``simplify``
    samples a multiplier against the dataset's auto tolerance; the resolved
    tolerance is recorded in the row, not the multiplier.
    """
    rng = np.random.default_rng(TRIAL_BASE_SEED + trial)
    sampled = {}
    for attack in ATTACKS:
        if attack == "none":
            sampled[attack] = {}
            continue
        specs = VECTOR_TRIAL_INTERVALS.get(attack)
        if not specs:
            sampled[attack] = dict(ATTACK_DEFAULTS.get(attack, {}))
            continue
        sampled[attack] = {name: float(rng.uniform(lo, hi)) for name, (lo, hi) in specs.items()}
    return sampled


# --------------------------------------------------------------------------- #
# shapefile helpers                                                            #
# --------------------------------------------------------------------------- #


def _read_gdf(shp_path):
    import geopandas as gpd

    return gpd.read_file(shp_path)


def _write_gdf(gdf, output_path):
    """Write a GeoDataFrame with the same pandas 3.x dtype fix as embed.py."""
    out_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(out_dir, exist_ok=True)
    for col in gdf.columns:
        if col == gdf.geometry.name:
            continue
        col_dtype = gdf[col].dtype
        if hasattr(col_dtype, "storage") or "StringDtype" in str(col_dtype) or "ArrowDtype" in str(col_dtype):
            gdf[col] = gdf[col].astype(object)
    gdf.to_file(output_path)
    return output_path


def _default_output(shp_path, tag):
    root, ext = os.path.splitext(str(shp_path))
    return f"{root}_{tag}{ext or '.shp'}"


def _vertex_centroid(gdf):
    """Vertex-count mean of all coordinates — the scale-attack origin."""
    from shapely import get_coordinates

    coords = get_coordinates(gdf.geometry.values)
    if coords.size == 0:
        return (0.0, 0.0)
    mean = coords.mean(axis=0)
    return (float(mean[0]), float(mean[1]))


# --------------------------------------------------------------------------- #
# attacks (each reads ``shp_path`` and writes a new shapefile)                  #
# --------------------------------------------------------------------------- #


def attack_translate(shp_path, dx=0.005, dy=0.003, output_path=None):
    """Whole-map translation by (dx, dy) degrees.

    Applied the way a user tool would: shapely affine on doubles, feature by
    feature (the legacy scheme's absolute-coordinate anchors break under it;
    D-QIM's difference-domain anchors do not).
    """
    from shapely.affinity import translate

    gdf = _read_gdf(shp_path)
    gdf.geometry = gdf.geometry.apply(lambda g: translate(g, xoff=dx, yoff=dy))
    return _write_gdf(gdf, output_path or _default_output(shp_path, "translate"))


def attack_scale(shp_path, factor=2.0, output_path=None):
    """Scale the whole map by ``factor`` around its vertex centroid."""
    from shapely.affinity import scale

    gdf = _read_gdf(shp_path)
    origin = _vertex_centroid(gdf)
    gdf.geometry = gdf.geometry.apply(lambda g: scale(g, xfact=factor, yfact=factor, origin=origin))
    return _write_gdf(gdf, output_path or _default_output(shp_path, "scale"))


def _drop_line_coords(coords, keep_mod):
    arr = np.asarray(coords, dtype=float)
    keep = np.arange(len(arr)) % keep_mod != 0
    return arr[keep]


def _drop_ring_coords(coords, keep_mod):
    """Drop from a closed ring; returns None when the ring would degenerate.

    The ring's explicit closure (last point duplicates the first) is preserved
    by re-appending the first kept vertex, so the result stays a legal ring.
    """
    arr = np.asarray(coords, dtype=float)
    core = arr[:-1]
    keep = np.arange(len(core)) % keep_mod != 0
    core = core[keep]
    if len(core) < 3:
        return None
    return np.vstack([core, core[:1]])


def _drop_vertices_geom(geom, keep_mod):
    """Deterministically delete every ``keep_mod``-th vertex of one geometry.

    Legality is preserved: lines below 2 points, rings below 3, invalid
    polygons and emptied multi-parts fall back to the original geometry (or
    drop the degenerate part respectively).
    """
    from shapely.geometry import LinearRing, LineString, MultiLineString, MultiPolygon, Polygon

    if geom.is_empty:
        return geom
    if isinstance(geom, LineString):
        coords = _drop_line_coords(geom.coords, keep_mod)
        return LineString(coords) if len(coords) >= 2 else geom
    if isinstance(geom, LinearRing):
        coords = _drop_ring_coords(geom.coords, keep_mod)
        return LinearRing(coords) if coords is not None else geom
    if isinstance(geom, Polygon):
        shell = _drop_ring_coords(geom.exterior.coords, keep_mod)
        if shell is None:
            return geom
        holes = []
        for interior in geom.interiors:
            ring = _drop_ring_coords(interior.coords, keep_mod)
            if ring is not None:
                holes.append(ring)
        candidate = Polygon(shell, holes)
        return candidate if candidate.is_valid else geom
    if isinstance(geom, (MultiLineString, MultiPolygon)):
        parts = [_drop_vertices_geom(part, keep_mod) for part in geom.geoms]
        parts = [p for p in parts if not p.is_empty]
        if not parts:
            return geom
        candidate = type(geom)(parts)
        return candidate if candidate.is_valid else geom
    return geom


def attack_vertex_drop(shp_path, pct=0.05, output_path=None):
    """Destroy ``pct`` of the vertices deterministically: every ``1/pct``-th one."""
    gdf = _read_gdf(shp_path)
    keep_mod = max(2, round(1.0 / float(pct))) if pct and pct > 0 else 2
    gdf.geometry = gdf.geometry.apply(lambda g: _drop_vertices_geom(g, keep_mod))
    return _write_gdf(gdf, output_path or _default_output(shp_path, "vertex_drop"))


def _noise_coords(coords, rng, sigma):
    arr = np.asarray(coords, dtype=float)
    return arr + rng.normal(0.0, sigma, arr.shape)


def _noise_ring_coords(coords, rng, sigma):
    arr = np.asarray(coords, dtype=float)
    core = arr[:-1] + rng.normal(0.0, sigma, arr[:-1].shape)
    return np.vstack([core, core[:1]])


def _noise_geom(geom, rng, sigma):
    from shapely.geometry import LinearRing, LineString, MultiLineString, MultiPoint, MultiPolygon, Point, Polygon

    try:
        if geom.is_empty:
            return geom
        if isinstance(geom, Point):
            return Point(_noise_coords(geom.coords, rng, sigma)[0])
        if isinstance(geom, MultiPoint):
            return MultiPoint(_noise_coords(geom.coords, rng, sigma))
        if isinstance(geom, LineString):
            return LineString(_noise_coords(geom.coords, rng, sigma))
        if isinstance(geom, LinearRing):
            return LinearRing(_noise_ring_coords(geom.coords, rng, sigma))
        if isinstance(geom, Polygon):
            shell = _noise_ring_coords(geom.exterior.coords, rng, sigma)
            holes = [_noise_ring_coords(ring.coords, rng, sigma) for ring in geom.interiors]
            candidate = Polygon(shell, holes)
            return candidate if candidate.is_valid else geom
        if isinstance(geom, (MultiLineString, MultiPolygon)):
            parts = [_noise_geom(part, rng, sigma) for part in geom.geoms]
            candidate = type(geom)(parts)
            return candidate if candidate.is_valid else geom
    except Exception:
        return geom
    return geom


def attack_noise(shp_path, sigma=1e-9, output_path=None, seed=NOISE_SEED):
    """Gaussian coordinate noise; fixed seed, deterministic per input order."""
    gdf = _read_gdf(shp_path)
    rng = np.random.default_rng(seed)
    gdf.geometry = gdf.geometry.apply(lambda g: _noise_geom(g, rng, sigma))
    return _write_gdf(gdf, output_path or _default_output(shp_path, "noise"))


def _resolve_tolerance(gdf, tolerance):
    if tolerance is not None:
        return float(tolerance)
    minx, miny, maxx, maxy = gdf.total_bounds
    return float(np.hypot(maxx - minx, maxy - miny)) * 1e-4


def default_simplify_tolerance(shp_path):
    """Auto tolerance used when ``attack_simplify`` is called with None."""
    return _resolve_tolerance(_read_gdf(shp_path), None)


def _simplify_geom(geom, tolerance):
    try:
        candidate = geom.simplify(tolerance, preserve_topology=True)
    except Exception:
        return geom
    return geom if candidate.is_empty else candidate


def attack_simplify(shp_path, tolerance=None, output_path=None):
    """Douglas-Peucker simplification with ``preserve_topology=True``.

    ``tolerance=None`` resolves to bounding-box diagonal x 1e-4 for this input.
    """
    gdf = _read_gdf(shp_path)
    tolerance = _resolve_tolerance(gdf, tolerance)
    gdf.geometry = gdf.geometry.apply(lambda g: _simplify_geom(g, tolerance))
    return _write_gdf(gdf, output_path or _default_output(shp_path, "simplify"))


_ATTACK_FUNCTIONS = {
    "translate": attack_translate,
    "scale": attack_scale,
    "vertex_drop": attack_vertex_drop,
    "noise": attack_noise,
    "simplify": attack_simplify,
}


def _ordered_attacks(attacks):
    """The no-attack baseline first, then the rest in caller order."""
    rest = [a for a in attacks if a != "none"]
    return (["none"] if "none" in attacks else []) + rest


# --------------------------------------------------------------------------- #
# matrix orchestration                                                         #
# --------------------------------------------------------------------------- #


def _unzip_first_shp(zip_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(out_dir)
    for name in sorted(os.listdir(out_dir)):
        if name.lower().endswith(".shp"):
            return os.path.join(out_dir, name)
    raise ValueError(f"no .shp in artifact zip: {zip_path}")


def _image_bits(image_path):
    """Flatten an image into a 0/1 bit sequence (threshold at 128)."""
    from PIL import Image

    arr = np.asarray(Image.open(image_path).convert("L"))
    return (arr > 127).astype(int).flatten()


def _row(scheme, attack, attack_params, decode_success, nc=None, ber=None, duration_ms=None, error=None, trial=1):
    return {
        "scheme": scheme,
        "attack": attack,
        "trial": trial,
        "attack_params": attack_params,
        "decode_success": decode_success,
        "nc": nc,
        "ber": ber,
        "duration_ms": duration_ms,
        "error": error,
    }


def _embed_stego(scheme, base_shp, qr_png, work_dir):
    """Embed ``scheme``'s watermark; returns ``(stego_shp, vr, side_length)``."""
    if scheme == "legacy":
        from algorithm.embed import embed
    elif scheme == "dqim1":
        from algorithm.vector_dqim import embed_dqim as embed
    else:
        raise ValueError(f"unknown scheme: {scheme!r}")
    result = embed(base_shp, qr_png, output_dir=os.path.join(work_dir, f"embed_{scheme}"))
    stego_shp = _unzip_first_shp(result["zip_path"], os.path.join(work_dir, f"stego_{scheme}"))
    return stego_shp, result["vr"], int(result["side_length"])


def _extract_watermark(scheme, attacked_shp, vr, side_length, out_dir):
    """Run the scheme's extractor; returns the rebuilt watermark PNG path."""
    if scheme == "legacy":
        from algorithm.extract import extract
    elif scheme == "dqim1":
        from algorithm.vector_dqim import extract_dqim as extract
    else:
        raise ValueError(f"unknown scheme: {scheme!r}")
    _shp_out, wm_png = extract(attacked_shp, vr, side_length=side_length, output_dir=out_dir)
    return wm_png


def _trial_attack_params(attack, trial, trials, attack_input_shp):
    """The real attack-parameter dict for one (attack, trial) cell.

    ``trials == 1`` keeps the documented ``ATTACK_DEFAULTS`` (with the simplify
    tolerance resolved against the actual input). ``trials > 1`` draws from
    ``sample_trial_params``; the noise attack additionally gets its per-trial
    fixed seed (``NOISE_SEED + trial``) and simplify resolves its tolerance
    against the dataset's auto tolerance x the sampled multiplier.
    """
    if trials == 1:
        params = dict(ATTACK_DEFAULTS[attack])
        if attack == "simplify":
            params["tolerance"] = default_simplify_tolerance(attack_input_shp)
        return params
    params = dict(sample_trial_params(trial)[attack])
    if attack == "none":
        return params
    if attack == "simplify":
        return {"tolerance": default_simplify_tolerance(attack_input_shp) * params["tolerance_multiplier"]}
    if attack == "noise":
        params["seed"] = NOISE_SEED + trial
    return params


def _unresolved_trial_params(attack, trial, trials):
    """Recorded params when the cell never reached its attack (embed failure)."""
    if trials == 1:
        return dict(ATTACK_DEFAULTS[attack])
    params = dict(sample_trial_params(trial)[attack])
    if attack == "noise":
        params["seed"] = NOISE_SEED + trial
    return params


def _run_scheme(scheme, base_shp, base_scheme_data, qr_png, attacks, payload_text, orig_bits, work_dir, trials=1):
    from algorithm.quality_metrics import compute_ber, compute_nc
    from resource.watermark_utils import decode_qr_from_image

    scheme_dir = os.path.join(work_dir, f"scheme_{scheme}")
    os.makedirs(scheme_dir, exist_ok=True)

    precomputed = (base_scheme_data or {}).get(scheme)
    rows = []
    for trial in range(1, trials + 1):
        trial_dir = os.path.join(scheme_dir, f"trial_{trial}")
        os.makedirs(trial_dir, exist_ok=True)
        # Every trial embeds its own stego: each trial is an independent
        # replicate with its own attack copies, never cumulative state.
        try:
            if precomputed:
                stego_shp = precomputed["stego_shp"]
                vr = precomputed["vr"]
                side_length = int(precomputed["side_length"])
            else:
                stego_shp, vr, side_length = _embed_stego(scheme, base_shp, qr_png, trial_dir)
        except Exception as e:
            logging.exception("robustness matrix: embed failed for scheme %s trial %s", scheme, trial)
            error = f"embed failed: {e}"[:255]
            rows.extend(
                _row(scheme, attack, _unresolved_trial_params(attack, trial, trials), False, error=error, trial=trial)
                for attack in attacks
            )
            continue

        for attack in attacks:
            started = time.perf_counter()
            params = None
            try:
                params = _trial_attack_params(attack, trial, trials, stego_shp)
                if attack == "none":
                    attacked_shp = stego_shp
                else:
                    attacked_shp = _ATTACK_FUNCTIONS[attack](
                        stego_shp,
                        output_path=os.path.join(trial_dir, f"attacked_{scheme}_{attack}.shp"),
                        **params,
                    )
                wm_png = _extract_watermark(
                    scheme, attacked_shp, vr, side_length, os.path.join(trial_dir, f"extract_{attack}")
                )
                text = decode_qr_from_image(wm_png)
                duration_ms = int((time.perf_counter() - started) * 1000)
                if text is None:
                    rows.append(_row(scheme, attack, params, False, duration_ms=duration_ms, trial=trial))
                    continue
                ext_bits = _image_bits(wm_png)
                nc = compute_nc(orig_bits, ext_bits)
                ber = compute_ber(orig_bits, ext_bits)
                rows.append(
                    _row(
                        scheme,
                        attack,
                        params,
                        text == payload_text,
                        nc=nc,
                        ber=ber,
                        duration_ms=duration_ms,
                        trial=trial,
                    )
                )
            except Exception as e:
                logging.exception("robustness matrix: cell failed scheme=%s attack=%s trial=%s", scheme, attack, trial)
                duration_ms = int((time.perf_counter() - started) * 1000)
                if params is None:
                    params = _unresolved_trial_params(attack, trial, trials)
                rows.append(
                    _row(scheme, attack, params, False, duration_ms=duration_ms, error=str(e)[:255], trial=trial)
                )
    return rows


def run_matrix(base_shp, base_scheme_data=None, schemes=None, attacks=None, payload_text=None, work_dir=None, trials=1):
    """Run the full (scheme x attack x trial) vector robustness matrix; returns row dicts.

    The payload QR is rendered once from ``payload_text`` (via
    ``delivery.qr2.render_v2_qr_png`` — the same renderer as the delivery
    chain) and serves as the ground-truth watermark every scheme embeds and
    every NC/BER is computed against. For each scheme every trial embeds its
    own stego shapefile; the no-attack baseline is measured first, then each
    requested attack runs on its own copy of that trial's stego.

    ``trials`` (>= 1) is the number of independent replicates per (scheme,
    attack) cell. With ``trials > 1``, trial t (1-based, per-row ``trial``)
    samples the documented parameter intervals with the fixed seed
    ``TRIAL_BASE_SEED + t`` via ``sample_trial_params`` — same request, same
    rows, bit for bit. ``trials == 1`` keeps the documented ``ATTACK_DEFAULTS``
    (the interval midpoints) exactly as the pre-trials engine did.

    ``base_scheme_data`` optionally maps scheme -> precomputed
    ``{"stego_shp", "vr", "side_length"}`` so a caller can reuse an earlier
    embed result instead of embedding again (the same stego then serves every
    trial); pass None to embed fresh per trial.

    Returns one row dict per (scheme, attack, trial): ``{scheme, attack, trial,
    attack_params, nc, ber, decode_success, duration_ms, error}`` — None
    metrics mean "not measured" (pending in the DB sense); nothing is written
    to any database here.
    """
    if not payload_text:
        raise ValueError("payload_text is required")
    if work_dir is None:
        raise ValueError("work_dir is required")
    if isinstance(trials, bool) or not isinstance(trials, int) or trials < 1:
        raise ValueError(f"trials must be a positive integer, got {trials!r}")
    schemes = list(schemes or SCHEMES)
    attacks = _ordered_attacks(list(attacks or ATTACKS))

    from delivery.qr2 import render_v2_qr_png

    os.makedirs(work_dir, exist_ok=True)
    qr_png = os.path.join(work_dir, "payload_qr.png")
    _png_path, side = render_v2_qr_png(payload_text, qr_png)
    logging.info("robustness matrix: payload QR rendered (%dx%d px)", side, side)
    orig_bits = _image_bits(qr_png)

    rows = []
    for scheme in schemes:
        rows.extend(
            _run_scheme(scheme, base_shp, base_scheme_data, qr_png, attacks, payload_text, orig_bits, work_dir, trials)
        )
    return rows
