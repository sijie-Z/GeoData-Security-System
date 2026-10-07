"""Attack-strength ladders for the WAVES-style robustness sweep (feat_strength_sweep).

A "sweep" run expands every attack of the matrix engines
(``algorithm/robustness.py`` vector attacks, ``algorithm/robustness_raster.py``
image attacks) into ``SWEEP_TIER_COUNT`` fixed intensity tiers stepping from
mild to severe, so one run yields a detection-rate curve per attack
(x = tier, y = decode-success rate) and its collapse point, instead of a single
point. The ladders live here — not in the engines — because they are lab
policy, not algorithm logic; the engines only consume ``sweep_params`` output.

Tier values are in each attack function's own units (read off its signature;
see ``algorithm/robustness.py`` / ``algorithm/robustness_raster.py``):

  * vector translate — degrees, ``dx = dy = delta`` (a real whole-map shift);
  * vector scale — dimensionless factor around the vertex centroid;
  * vector vertex_drop — fraction of vertices deleted (``pct``; the attack maps
    it to every ``round(1/pct)``-th vertex);
  * vector noise — coordinate sigma in degrees. The QIM cell of both schemes is
    ``R = 1e-7`` (``algorithm/embed.py`` / ``algorithm/vector_dqim.py``) and the
    documented matrix default is ``sigma = 1e-9``, so the informative band spans
    ``1e-9 -> 1e-5``: tiers below the grid cell survive, tiers far above it
    collapse (tier values measured on the matrix fixture, see the comments);
  * vector simplify — Douglas-Peucker tolerance in degrees;
  * raster jpeg — PIL quality, lower = harsher;
  * raster resize — bilinear downsample factor, lower = harsher;
  * raster crop — kept fraction of each side, lower = harsher;
  * raster rotate — degrees (bilinear, expand=False);
  * raster noise — additive Gaussian sigma in the 0-255 pixel domain;
  * raster blur — PIL Gaussian blur radius.

Reproducibility: only the ``noise`` attacks of each kind draw random numbers.
Their seed is derived deterministically from ``(kind, attack, strength_index,
trial)`` by ``sweep_seed`` — an extension of the matrix rule ``seed = 11 +
trial`` (``NOISE_SEED``/``RASTER_NOISE_SEED``) with the tier and attack ordinal
folded in — so the same sweep request reproduces every row bit for bit. The
exact values are pinned by ``tests/test_robustness_sweep.py``.

``none`` (the no-attack baseline) is deliberately absent from every ladder: the
baseline is not a strength tier. Sweep runs reject it at the API boundary and
engine boundary, and the ladder dicts double as the registry of sweepable
attacks per kind.
"""

SWEEP_TIER_COUNT = 5

# Sweep seed rule: ``seed = SWEEP_SEED_BASE + trial + 100 * strength_index +
# 1000 * attack_ordinal`` — the matrix rule "11 + trial" kept as the base, with
# the tier and the attack's canonical ordinal making every (attack, tier,
# trial) cell's stream unique and reproducible from the request alone.
SWEEP_SEED_BASE = 11
_SWEEP_SEED_ATTACK_ORDINALS = {
    "vector": {"translate": 1, "scale": 2, "vertex_drop": 3, "noise": 4, "simplify": 5},
    "raster": {"jpeg": 1, "resize": 2, "crop": 3, "rotate": 4, "noise": 5, "blur": 6},
}


def sweep_seed(kind, attack, strength_index, trial):
    """Deterministic Gaussian-noise seed for one sweep cell.

    ``kind`` is ``"vector"`` | ``"raster"`` (the two ``noise`` attacks otherwise
    share a name); ``strength_index`` is 0-based, ``trial`` is 1-based.
    """
    ordinal = _SWEEP_SEED_ATTACK_ORDINALS[kind][attack]
    return SWEEP_SEED_BASE + trial + 100 * strength_index + 1000 * ordinal


# --------------------------------------------------------------------------- #
# vector ladders (units of algorithm/robustness.py's attack functions)          #
# --------------------------------------------------------------------------- #

# translate: 0.0005° ≈ 55 m at the equator — mild; 0.008° exceeds the
# E1-measured legacy-lethal shift (dx=0.005, dy=0.003) used as the matrix
# default, so the ladder brackets the documented lethality of the legacy
# scheme. dx = dy = delta keeps the shift direction-free.
VECTOR_TRANSLATE_LADDER = (
    {"label": "平移 δ=0.0005°", "params": {"dx": 0.0005, "dy": 0.0005}},
    {"label": "平移 δ=0.001°", "params": {"dx": 0.001, "dy": 0.001}},
    {"label": "平移 δ=0.002°", "params": {"dx": 0.002, "dy": 0.002}},
    {"label": "平移 δ=0.004°", "params": {"dx": 0.004, "dy": 0.004}},
    {"label": "平移 δ=0.008°", "params": {"dx": 0.008, "dy": 0.008}},
)

# scale: near-1 shrinkage factors. Both schemes' seeds anchor on the R = 1e-7
# grid of coordinate differences (~1e-3° for the matrix fixture), so a factor
# within 1e-4 of 1.0 keeps most difference cells and the collapse — where it
# exists — happens in the last two tiers (measured; see the calibration note
# in the task report). Factor 1.0 itself would be the identity, not a tier.
VECTOR_SCALE_LADDER = (
    {"label": "缩放 ×0.9999", "params": {"factor": 0.9999}},
    {"label": "缩放 ×0.9995", "params": {"factor": 0.9995}},
    {"label": "缩放 ×0.999", "params": {"factor": 0.999}},
    {"label": "缩放 ×0.995", "params": {"factor": 0.995}},
    {"label": "缩放 ×0.99", "params": {"factor": 0.99}},
)

# vertex_drop: 1% ⇔ every 100th vertex, 20% ⇔ every 5th (the attack's keep_mod
# mapping). The matrix default (5%) and the documented trial interval (3-8%)
# sit inside this ladder, so its ends extend beyond the documented range.
VECTOR_VERTEX_DROP_LADDER = (
    {"label": "丢弃 1%", "params": {"pct": 0.01}},
    {"label": "丢弃 2%", "params": {"pct": 0.02}},
    {"label": "丢弃 5%", "params": {"pct": 0.05}},
    {"label": "丢弃 10%", "params": {"pct": 0.1}},
    {"label": "丢弃 20%", "params": {"pct": 0.2}},
)

# noise: calibrated against the R = 1e-7 cell (both schemes anchor their QIM
# seeds on it) and the documented noise facts: the matrix default is 1e-9 and
# the multi-trial interval is (5e-10, 2e-9) — measured: the 413k-vertex E2E
# vector survives sigma=1e-9 (NC 0.9951) and loses decoding at 1e-8, while a
# small 60x300 fixture already fails at 1e-9 (fewer votes per symbol -> noise
# tolerance grows with dataset size). The ladder therefore anchors its lower
# half on the documented interval (5e-10 / 1e-9 / 2e-9) and extends one and
# two decades beyond it (1e-8 / 1e-7) for the collapse.
VECTOR_NOISE_LADDER = (
    {"label": "σ=5e-10°", "params": {"sigma": 5e-10}},
    {"label": "σ=1e-9°", "params": {"sigma": 1e-9}},
    {"label": "σ=2e-9°", "params": {"sigma": 2e-9}},
    {"label": "σ=1e-8°", "params": {"sigma": 1e-8}},
    {"label": "σ=1e-7°", "params": {"sigma": 1e-7}},
)

# simplify: Douglas-Peucker tolerance in degrees. The matrix auto tolerance is
# bounding-box-diagonal x 1e-4 (≈8e-5° for the matrix fixture); the ladder
# starts right above it and ends at a tolerance that flattens the fixture's
# ~1e-3° vertex jitter (severe for any real geometry).
VECTOR_SIMPLIFY_LADDER = (
    {"label": "容差 1e-4°", "params": {"tolerance": 1e-4}},
    {"label": "容差 5e-4°", "params": {"tolerance": 5e-4}},
    {"label": "容差 1e-3°", "params": {"tolerance": 1e-3}},
    {"label": "容差 2e-3°", "params": {"tolerance": 2e-3}},
    {"label": "容差 5e-3°", "params": {"tolerance": 5e-3}},
)

VECTOR_SWEEP_LADDERS = {
    "translate": VECTOR_TRANSLATE_LADDER,
    "scale": VECTOR_SCALE_LADDER,
    "vertex_drop": VECTOR_VERTEX_DROP_LADDER,
    "noise": VECTOR_NOISE_LADDER,
    "simplify": VECTOR_SIMPLIFY_LADDER,
}


# --------------------------------------------------------------------------- #
# raster ladders (units of algorithm/robustness_raster.py's r_* functions)      #
# --------------------------------------------------------------------------- #

# jpeg: PIL quality must be an integer; 95 is nearly lossless, 30 visibly
# destroys LSB-style payloads.
RASTER_JPEG_LADDER = (
    {"label": "质量 95", "params": {"quality": 95}},
    {"label": "质量 85", "params": {"quality": 85}},
    {"label": "质量 70", "params": {"quality": 70}},
    {"label": "质量 50", "params": {"quality": 50}},
    {"label": "质量 30", "params": {"quality": 30}},
)

# resize: factors 0.9 -> 0.25 of the stego size (never scaled back up; the
# extractor sees the real attacked size).
RASTER_RESIZE_LADDER = (
    {"label": "缩放 ×0.9", "params": {"factor": 0.9}},
    {"label": "缩放 ×0.75", "params": {"factor": 0.75}},
    {"label": "缩放 ×0.5", "params": {"factor": 0.5}},
    {"label": "缩放 ×0.35", "params": {"factor": 0.35}},
    {"label": "缩放 ×0.25", "params": {"factor": 0.25}},
)

# crop: center crop keeping a fraction of each side, 95% -> 50%.
RASTER_CROP_LADDER = (
    {"label": "保留 95%", "params": {"keep": 0.95}},
    {"label": "保留 90%", "params": {"keep": 0.9}},
    {"label": "保留 80%", "params": {"keep": 0.8}},
    {"label": "保留 65%", "params": {"keep": 0.65}},
    {"label": "保留 50%", "params": {"keep": 0.5}},
)

# rotate: bilinear, expand=False (frame size unchanged). Sub-degree tiers are
# the scan/straightening regime; 10° is clearly severe.
RASTER_ROTATE_LADDER = (
    {"label": "旋转 0.5°", "params": {"deg": 0.5}},
    {"label": "旋转 1°", "params": {"deg": 1.0}},
    {"label": "旋转 2°", "params": {"deg": 2.0}},
    {"label": "旋转 5°", "params": {"deg": 5.0}},
    {"label": "旋转 10°", "params": {"deg": 10.0}},
)

# noise: sigma in the 0-255 pixel domain; matrix default 5, documented trial
# interval 3-8, ladder extends both ends.
RASTER_NOISE_LADDER = (
    {"label": "σ=2", "params": {"sigma": 2.0}},
    {"label": "σ=5", "params": {"sigma": 5.0}},
    {"label": "σ=10", "params": {"sigma": 10.0}},
    {"label": "σ=20", "params": {"sigma": 20.0}},
    {"label": "σ=35", "params": {"sigma": 35.0}},
)

# blur: PIL Gaussian radius; matrix default 3.
RASTER_BLUR_LADDER = (
    {"label": "模糊半径 0.5", "params": {"radius": 0.5}},
    {"label": "模糊半径 1", "params": {"radius": 1.0}},
    {"label": "模糊半径 2", "params": {"radius": 2.0}},
    {"label": "模糊半径 3", "params": {"radius": 3.0}},
    {"label": "模糊半径 5", "params": {"radius": 5.0}},
)

RASTER_SWEEP_LADDERS = {
    "jpeg": RASTER_JPEG_LADDER,
    "resize": RASTER_RESIZE_LADDER,
    "crop": RASTER_CROP_LADDER,
    "rotate": RASTER_ROTATE_LADDER,
    "noise": RASTER_NOISE_LADDER,
    "blur": RASTER_BLUR_LADDER,
}


# --------------------------------------------------------------------------- #
# accessors                                                                     #
# --------------------------------------------------------------------------- #


def ladders_for_kind(kind):
    """Ladder registry for ``"vector"`` | ``"raster"``."""
    return VECTOR_SWEEP_LADDERS if kind == "vector" else RASTER_SWEEP_LADDERS


def sweep_params(kind, attack, strength_index, trial):
    """The real attack parameters for one sweep cell (logged per row).

    Ladder params as-is; the ``noise`` attacks additionally receive their fixed
    per-(attack, tier, trial) seed from ``sweep_seed``.
    """
    tier = ladders_for_kind(kind)[attack][strength_index]
    params = dict(tier["params"])
    if attack == "noise":
        params["seed"] = sweep_seed(kind, attack, strength_index, trial)
    return params


def sweep_tier_params(kind, attack, strength_index):
    """Ladder params for one tier without any per-trial seed (pending rows).

    Used when the run is queued: pre-inserted rows carry the tier's documented
    parameters; the worker replaces them with ``sweep_params`` output (real
    params incl. the noise seed) as each cell completes.
    """
    return dict(ladders_for_kind(kind)[attack][strength_index]["params"])


def sweep_ladders_payload(kind, attacks):
    """``{attack: [{index, label, params}, ...]}`` for the run-detail response.

    ``attacks`` keep the caller's order; names without a ladder are skipped
    (none should exist — sweep runs reject ``none`` and unknown attacks).
    """
    ladders = ladders_for_kind(kind)
    return {
        attack: [
            {"index": index, "label": tier["label"], "params": dict(tier["params"])}
            for index, tier in enumerate(ladders[attack])
        ]
        for attack in attacks
        if attack in ladders
    }
