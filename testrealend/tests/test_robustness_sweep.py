"""Tests for the WAVES-style attack-strength sweep (feat_strength_sweep).

Engine: ``algorithm/robustness_sweep.py`` (the 5-tier ladders + the
``(kind, attack, strength_index, trial)`` seed rule) feeding the sweep runners
of ``algorithm/robustness.py`` (vector) / ``algorithm/robustness_raster.py``
(raster), plus the ``mode="sweep"`` extension of ``POST /api/robustness/run``
and the ``mode``/``ladders`` extensions of the run detail/listing responses.
"""

import inspect
import json
from itertools import pairwise

import pytest

from algorithm.robustness_sweep import (
    RASTER_SWEEP_LADDERS,
    SWEEP_TIER_COUNT,
    VECTOR_SWEEP_LADDERS,
    sweep_params,
    sweep_seed,
)


def _build_matrix_payload():
    """Real v2 signed payload text (same construction as test_robustness)."""
    from datetime import UTC, datetime

    from crypto.keys import ensure_active_key
    from crypto.payload import build_qr_v2_text

    kid, _private_key = ensure_active_key()
    return build_qr_v2_text("gh" * 16, 4242, kid, int(datetime.now(UTC).timestamp()))


def _join_worker(run_id, timeout=300):
    """Join the background worker of a queued run (no polling races)."""
    import resource.robustness_resource as robustness_resource

    thread = robustness_resource._ACTIVE_RUNS.get(run_id)
    if thread is not None:
        thread.join(timeout=timeout)
        assert not thread.is_alive(), "robustness worker did not finish in time"


# =========================================================================== #
# Ladder registry integrity                                                    #
# =========================================================================== #

# The real attack functions each ladder entry's params must fit (signature
# check below); this map is the full sweepable attack set per kind.
VECTOR_ATTACK_FUNCTIONS = {
    "translate": "attack_translate",
    "scale": "attack_scale",
    "vertex_drop": "attack_vertex_drop",
    "noise": "attack_noise",
    "simplify": "attack_simplify",
}
RASTER_ATTACK_FUNCTIONS = {
    "jpeg": "r_jpeg",
    "resize": "r_resize",
    "crop": "r_crop",
    "rotate": "r_rotate",
    "noise": "r_noise",
    "blur": "r_blur",
}

# Params that carry paths/plumbing rather than attack intensity — a ladder must
# never set them. ("seed" is injected per (attack, tier, trial) by sweep_params,
# never authored in the ladder.)
_NON_INTENSITY_PARAMS = {"shp_path", "stego_path", "output_path", "base_profile", "seed"}

# Severity direction per attack: the params key whose value must be strictly
# monotone from tier 0 (mild) to tier 4 (severe). 1 = ascending, -1 = descending.
_SEVERITY_DIRECTION = {
    "translate": ("dx", 1),
    "scale": ("factor", -1),
    "vertex_drop": ("pct", 1),
    "noise": ("sigma", 1),
    "simplify": ("tolerance", 1),
    "jpeg": ("quality", -1),
    "resize": ("factor", -1),
    "crop": ("keep", -1),
    "rotate": ("deg", 1),
    "blur": ("radius", 1),
}


def _attack_function_map(kind):
    import algorithm.robustness as vector_engine
    import algorithm.robustness_raster as raster_engine

    names = VECTOR_ATTACK_FUNCTIONS if kind == "vector" else RASTER_ATTACK_FUNCTIONS
    module = vector_engine if kind == "vector" else raster_engine
    return {attack: getattr(module, fn_name) for attack, fn_name in names.items()}


class TestSweepLadders:
    """Registry completeness: 5 tiers per attack, real params, readable labels."""

    def test_registries_cover_exactly_the_sweepable_attacks(self):
        assert set(VECTOR_SWEEP_LADDERS) == set(VECTOR_ATTACK_FUNCTIONS)
        assert set(RASTER_SWEEP_LADDERS) == set(RASTER_ATTACK_FUNCTIONS)
        # "none" (the no-attack baseline) is deliberately not a strength tier.
        assert "none" not in VECTOR_SWEEP_LADDERS
        assert "none" not in RASTER_SWEEP_LADDERS

    @pytest.mark.parametrize("kind", ["vector", "raster"])
    def test_every_attack_has_exactly_five_labelled_serializable_tiers(self, kind):
        ladders = VECTOR_SWEEP_LADDERS if kind == "vector" else RASTER_SWEEP_LADDERS
        for attack, tiers in ladders.items():
            assert len(tiers) == SWEEP_TIER_COUNT, attack
            labels = []
            for tier in tiers:
                assert isinstance(tier["label"], str) and tier["label"].strip(), attack
                labels.append(tier["label"])
                assert isinstance(tier["params"], dict) and tier["params"], attack
                json.dumps(tier["params"])  # JSON-serializable (the DB column is JSON)
            assert len(set(labels)) == SWEEP_TIER_COUNT, f"duplicate labels for {attack}"

    @pytest.mark.parametrize("kind", ["vector", "raster"])
    def test_tier_params_match_attack_signatures(self, kind):
        for attack, fn in _attack_function_map(kind).items():
            signature_params = set(inspect.signature(fn).parameters)
            tiers = (VECTOR_SWEEP_LADDERS if kind == "vector" else RASTER_SWEEP_LADDERS)[attack]
            for tier in tiers:
                params = tier["params"]
                assert set(params) <= signature_params, f"{attack}: {set(params) - signature_params}"
                assert not (set(params) & _NON_INTENSITY_PARAMS), attack

    @pytest.mark.parametrize("kind", ["vector", "raster"])
    def test_tier_severity_is_strictly_monotone(self, kind):
        ladders = VECTOR_SWEEP_LADDERS if kind == "vector" else RASTER_SWEEP_LADDERS
        for attack, tiers in ladders.items():
            key, direction = _SEVERITY_DIRECTION[attack]
            values = [tier["params"][key] for tier in tiers]
            for before, after in pairwise(values):
                assert (after - before) * direction > 0, f"{attack}: {values} not strictly monotone"

    def test_sweep_params_injects_seed_for_noise_only(self):
        for kind in ("vector", "raster"):
            noise = sweep_params(kind, "noise", 2, 3)
            assert noise["seed"] == sweep_seed(kind, "noise", 2, 3)
            other = "translate" if kind == "vector" else "jpeg"
            assert "seed" not in sweep_params(kind, other, 2, 3)

    def test_sweep_params_returns_ladder_values_unmodified(self):
        for kind, ladders in (("vector", VECTOR_SWEEP_LADDERS), ("raster", RASTER_SWEEP_LADDERS)):
            for attack, tiers in ladders.items():
                for index, tier in enumerate(tiers):
                    params = sweep_params(kind, attack, index, 1)
                    expected = dict(tier["params"])
                    if attack == "noise":
                        expected.pop("seed", None)
                        params.pop("seed", None)
                    assert params == expected, (kind, attack, index)


class TestSweepSeed:
    """The (kind, attack, tier, trial) seed rule: pinned values + determinism."""

    def test_seed_formula_is_pinned(self):
        # seed = SWEEP_SEED_BASE(11) + trial + 100*tier + 1000*attack_ordinal;
        # vector ordinals: translate 1 .. simplify 5; raster: jpeg 1 .. blur 6.
        assert sweep_seed("vector", "noise", 0, 1) == 11 + 1 + 0 + 4000  # 4012
        assert sweep_seed("vector", "noise", 4, 3) == 11 + 3 + 400 + 4000  # 4414
        assert sweep_seed("raster", "noise", 2, 1) == 11 + 1 + 200 + 5000  # 5212
        assert sweep_seed("vector", "translate", 0, 1) == 11 + 1 + 1000  # 1012
        assert sweep_seed("raster", "blur", 4, 5) == 11 + 5 + 400 + 6000  # 6416

    def test_seed_is_deterministic_and_unique_per_cell(self):
        # "noise" is the only attack that consumes a seed (vector ordinal 4,
        # raster ordinal 5), so uniqueness is asserted across its cells.
        seen = []
        for kind in ("vector", "raster"):
            for tier in range(SWEEP_TIER_COUNT):
                for trial in range(1, 6):
                    first = sweep_seed(kind, "noise", tier, trial)
                    assert first == sweep_seed(kind, "noise", tier, trial)
                    seen.append(first)
        assert len(seen) == len(set(seen)), "seed collisions across sweep noise cells"


# =========================================================================== #
# Engine: real sweep runs                                                      #
# =========================================================================== #


class TestRasterSweepEngine:
    def _payload_qr(self, db, tmp_path):
        from algorithm.robustness_raster import render_raster_payload_qr

        text = _build_matrix_payload()
        qr_path, _side = render_raster_payload_qr(text, str(tmp_path / "payload_qr.png"))
        return qr_path

    def test_sweep_rows_fan_out_over_five_tiers(self, db, tmp_path):
        """1 scheme x 2 attacks x trials=1 -> exactly 10 rows, each tier twice."""
        from algorithm.robustness_raster import make_host_tif, run_raster_sweep

        qr_path = self._payload_qr(db, tmp_path)
        host = make_host_tif(str(tmp_path / "host.tif"))
        rows = run_raster_sweep(host, ["lsb"], ["jpeg", "resize"], qr_path, str(tmp_path / "work_sweep"), trials=1)
        assert len(rows) == 2 * SWEEP_TIER_COUNT
        from collections import Counter

        assert Counter(row["strength_index"] for row in rows) == Counter({i: 2 for i in range(SWEEP_TIER_COUNT)})
        for row in rows:
            assert isinstance(row["decode_success"], bool)
            assert row["duration_ms"] is not None and row["duration_ms"] >= 0
            # attack_params = that tier's real ladder params (+ the noise seed
            # for noise cells, not used here).
            ladder_params = RASTER_SWEEP_LADDERS[row["attack"]][row["strength_index"]]["params"]
            assert row["attack_params"] == ladder_params
        jpeg_qualities = {row["attack_params"]["quality"] for row in rows if row["attack"] == "jpeg"}
        assert jpeg_qualities == {tier["params"]["quality"] for tier in RASTER_SWEEP_LADDERS["jpeg"]}

    def test_sweep_rejects_none_and_unknown_attacks(self, db, tmp_path):
        from algorithm.robustness_raster import make_host_tif, run_raster_sweep

        qr_path = self._payload_qr(db, tmp_path)
        host = make_host_tif(str(tmp_path / "host.tif"))
        with pytest.raises(ValueError, match="none"):
            run_raster_sweep(host, ["lsb"], ["none"], qr_path, str(tmp_path / "work_none"))
        with pytest.raises(ValueError, match="unknown"):
            run_raster_sweep(host, ["lsb"], ["banana"], qr_path, str(tmp_path / "work_bad"))


class TestVectorSweepEngine:
    def test_dqim1_survives_the_translate_ladder(self, db, tmp_path):
        """D-QIM is translation-invariant: all five tiers decode with NC measured."""
        from algorithm.robustness import run_sweep

        shp = _make_sweep_shp(tmp_path / "dqim_sweep.shp")
        rows = run_sweep(
            shp,
            None,
            ["dqim1"],
            ["translate"],
            _build_matrix_payload(),
            str(tmp_path / "work_dqim_sweep"),
            trials=1,
        )
        assert len(rows) == SWEEP_TIER_COUNT
        for row in sorted(rows, key=lambda r: r["strength_index"]):
            assert row["decode_success"] is True, row
            assert row["nc"] is not None and 0.9 < float(row["nc"]) <= 1.0
            assert (
                row["attack_params"]["dx"] == VECTOR_SWEEP_LADDERS["translate"][row["strength_index"]]["params"]["dx"]
            )

    def test_sweep_rejects_none_and_unknown_attacks(self, db, tmp_path):
        from algorithm.robustness import run_sweep

        shp = _make_sweep_shp(tmp_path / "dqim_reject.shp")
        payload = _build_matrix_payload()
        with pytest.raises(ValueError, match="none"):
            run_sweep(shp, None, ["dqim1"], ["none"], payload, str(tmp_path / "w1"))
        with pytest.raises(ValueError, match="unknown"):
            run_sweep(shp, None, ["dqim1"], ["banana"], payload, str(tmp_path / "w2"))


def _make_sweep_shp(path, n_lines=40, n_pts=200, x0=116.0, y0=39.0, seed=7):
    """Smaller sibling of test_robustness._make_matrix_shp (same recipe)."""
    import geopandas as gpd
    import numpy as np
    from shapely.geometry import LineString

    rng = np.random.default_rng(seed)
    lines = []
    for i in range(n_lines):
        xs = x0 + i * 0.01 + np.cumsum(rng.uniform(-0.001, 0.001, n_pts))
        ys = y0 + i * 0.01 + np.cumsum(rng.uniform(-0.001, 0.001, n_pts))
        lines.append(LineString(np.column_stack([xs, ys])))
    gpd.GeoDataFrame({"fid": range(n_lines)}, geometry=lines, crs="EPSG:4326").to_file(str(path))
    return str(path)


# =========================================================================== #
# API: POST mode=sweep, detail mode/ladders, matrix regression                 #
# =========================================================================== #


class TestSweepApi:
    def test_raster_sweep_run_and_detail(self, client, db, auth_headers):
        resp = client.post(
            "/api/robustness/run",
            json={"kind": "raster", "mode": "sweep", "schemes": ["lsb"], "attacks": ["jpeg", "resize"], "trials": 1},
            headers=auth_headers,
        )
        assert resp.status_code == 202, resp.get_json()
        data = resp.get_json()["data"]
        assert data["mode"] == "sweep"
        assert data["total"] == 2 * SWEEP_TIER_COUNT
        run_id = data["run_id"]
        _join_worker(run_id)

        detail = client.get(f"/api/robustness/runs/{run_id}", headers=auth_headers)
        assert detail.status_code == 200
        run = detail.get_json()["run"]
        assert run["mode"] == "sweep"
        assert run["kind"] == "raster"
        assert run["done"] == run["total"] == 10

        ladders = run["ladders"]
        assert set(ladders) == {"jpeg", "resize"}
        for tiers in ladders.values():
            assert len(tiers) == SWEEP_TIER_COUNT
            assert [tier["index"] for tier in tiers] == list(range(SWEEP_TIER_COUNT))
            for tier in tiers:
                assert tier["label"].strip()
                assert isinstance(tier["params"], dict) and tier["params"]

        rows = run["rows"]
        assert len(rows) == 10
        assert {row["strength_index"] for row in rows} == set(range(SWEEP_TIER_COUNT))
        for row in rows:
            assert row["strength_index"] in range(SWEEP_TIER_COUNT)
            assert isinstance(row["decode_success"], bool)
            assert row["attack_params"] == RASTER_SWEEP_LADDERS[row["attack"]][row["strength_index"]]["params"]

        listing = client.get("/api/robustness/runs", headers=auth_headers)
        entry = next(e for e in listing.get_json()["runs"] if e["run_id"] == run_id)
        assert entry["mode"] == "sweep"

    def test_matrix_run_regression_strength_index_null_and_mode_matrix(self, client, db, auth_headers):
        """Same-parameter matrix run keeps the historical row set; strength_index stays NULL."""
        resp = client.post(
            "/api/robustness/run",
            json={"kind": "raster", "schemes": ["lsb"], "attacks": ["none", "jpeg"], "trials": 1},
            headers=auth_headers,
        )
        assert resp.status_code == 202, resp.get_json()
        data = resp.get_json()["data"]
        assert data["mode"] == "matrix"
        assert data["total"] == 2
        run_id = data["run_id"]
        _join_worker(run_id)

        run = client.get(f"/api/robustness/runs/{run_id}", headers=auth_headers).get_json()["run"]
        assert run["mode"] == "matrix"
        assert run["ladders"] == {}
        assert len(run["rows"]) == 2
        assert {(row["scheme"], row["attack"]) for row in run["rows"]} == {("lsb", "none"), ("lsb", "jpeg")}
        for row in run["rows"]:
            assert row["strength_index"] is None

        entry = next(
            e
            for e in client.get("/api/robustness/runs", headers=auth_headers).get_json()["runs"]
            if e["run_id"] == run_id
        )
        assert entry["mode"] == "matrix"

    def test_sweep_trials_default_and_clamp(self, client, db, auth_headers):
        """trials absent -> 3; trials=7 -> clamped to 5; rows scale with trials."""
        resp = client.post(
            "/api/robustness/run",
            json={"kind": "raster", "mode": "sweep", "schemes": ["lsb"], "attacks": ["jpeg"], "trials": 7},
            headers=auth_headers,
        )
        assert resp.status_code == 202, resp.get_json()
        data = resp.get_json()["data"]
        assert data["trials"] == 5
        assert data["total"] == SWEEP_TIER_COUNT * 5
        run_id = data["run_id"]
        _join_worker(run_id)
        run = client.get(f"/api/robustness/runs/{run_id}", headers=auth_headers).get_json()["run"]
        assert run["trials"] == 5
        assert len(run["rows"]) == SWEEP_TIER_COUNT * 5

        resp2 = client.post(
            "/api/robustness/run",
            json={"kind": "raster", "mode": "sweep", "schemes": ["lsb"], "attacks": ["jpeg"]},
            headers=auth_headers,
        )
        assert resp2.status_code == 202, resp2.get_json()
        data2 = resp2.get_json()["data"]
        assert data2["trials"] == 3
        assert data2["total"] == SWEEP_TIER_COUNT * 3
        _join_worker(data2["run_id"])

    def test_sweep_rejects_none(self, client, db, auth_headers):
        resp = client.post(
            "/api/robustness/run",
            json={"kind": "raster", "mode": "sweep", "schemes": ["lsb"], "attacks": ["none", "jpeg"]},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        msg = resp.get_json()["msg"]
        assert "none" in msg and "基线" in msg

    def test_invalid_mode_rejected(self, client, db, auth_headers):
        resp = client.post(
            "/api/robustness/run",
            json={"kind": "raster", "mode": "banana", "schemes": ["lsb"], "attacks": ["jpeg"]},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "mode" in resp.get_json()["msg"]

    def test_sweep_requires_admin(self, client, db):
        resp = client.post("/api/robustness/run", json={"kind": "raster", "mode": "sweep", "attacks": ["jpeg"]})
        assert resp.status_code in (401, 403)
