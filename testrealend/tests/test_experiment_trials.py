"""Multi-trial (trials) experiment surface: engines, endpoint and zombie sweep.

Covers the feat_experiment_trials contract:

  * vector / raster engines — ``trials`` parameterization (N x rows), per-trial
    parameter sampling inside the documented intervals, fixed-seed
    reproducibility (same request twice -> identical rows), per-trial stego /
    host generation, and the trials=1 legacy path (documented defaults);
  * Step 1b — seeded Gaussian attack noise is byte-reproducible per seed;
  * endpoint — ``trials`` validation (0 / 11 / string / >200 rows -> 400),
    expected ``data.total``, run-level ``trials`` key, and the summary
    aggregation block (hand-checked math);
  * Step 3b — starting a run sweeps zombie runs (all rows pending, no error)
    into ``error='interrupted (no active worker)'`` while leaving runs that
    made progress, or already carry an error, untouched.
"""

import numpy as np
import pytest

from tests.test_robustness import _build_matrix_payload, _make_matrix_shp


def _join_worker(run_id, timeout=120):
    import resource.robustness_resource as robustness_resource

    thread = robustness_resource._ACTIVE_RUNS.get(run_id)
    if thread is not None:
        thread.join(timeout=timeout)
        assert not thread.is_alive(), "robustness worker did not finish in time"


# =========================================================================== #
# Vector engine — trials parameterization and sampling                       #
# =========================================================================== #


class TestVectorTrialsEngine:
    def test_trials_multiplies_rows_and_records_trial(self, db, tmp_path):
        from algorithm.robustness import run_matrix

        shp = _make_matrix_shp(tmp_path / "trials_vec.shp")
        rows = run_matrix(
            shp,
            None,
            schemes=["dqim1"],
            attacks=["none", "translate", "noise"],
            trials=3,
            payload_text=_build_matrix_payload(),
            work_dir=str(tmp_path / "work_trials"),
        )
        assert len(rows) == 9, "trials=3 must produce 3x rows"
        per_attack = {}
        for row in rows:
            per_attack.setdefault(row["attack"], []).append(row["trial"])
        assert per_attack == {"none": [1, 2, 3], "translate": [1, 2, 3], "noise": [1, 2, 3]}
        for row in rows:
            assert row["decode_success"] is not None
            assert row["duration_ms"] is not None and row["duration_ms"] >= 0

    def test_trial_params_within_documented_intervals(self, db, tmp_path):
        from algorithm.robustness import default_simplify_tolerance, run_matrix

        shp = _make_matrix_shp(tmp_path / "intervals.shp")
        attacks = ["translate", "scale", "vertex_drop", "noise", "simplify"]
        rows = run_matrix(
            shp,
            None,
            schemes=["legacy"],
            attacks=attacks,
            trials=3,
            payload_text=_build_matrix_payload(),
            work_dir=str(tmp_path / "work_intervals"),
        )
        assert len(rows) == 15
        auto_tol = default_simplify_tolerance(shp)
        translate_params = set()
        for row in rows:
            params = row["attack_params"]
            if row["attack"] == "translate":
                assert 0.003 <= params["dx"] <= 0.008
                assert 0.002 <= params["dy"] <= 0.005
                translate_params.add((params["dx"], params["dy"]))
            elif row["attack"] == "scale":
                assert 1.5 <= params["factor"] <= 3.0
            elif row["attack"] == "vertex_drop":
                assert 0.03 <= params["pct"] <= 0.08
            elif row["attack"] == "noise":
                assert 5e-10 <= params["sigma"] <= 2e-9
                assert params["seed"] == 11 + row["trial"], "per-trial noise seed must be fixed to 11+trial"
            elif row["attack"] == "simplify":
                # tolerance = auto tolerance x U(0.5, 1.5); slack covers the
                # stego/source bounding-box drift introduced by embedding.
                ratio = params["tolerance"] / auto_tol
                assert 0.45 <= ratio <= 1.55, f"simplify tolerance ratio {ratio} outside the sampled band"
        assert len(translate_params) == 3, "the three trials must draw different parameters"

    def test_trials_reproducible_and_seed_sampled(self, db, tmp_path):
        from algorithm.robustness import run_matrix

        def _run(tag):
            return run_matrix(
                shp,
                None,
                schemes=["dqim1"],
                attacks=["none", "translate"],
                trials=2,
                payload_text=payload,
                work_dir=str(tmp_path / tag),
            )

        shp = _make_matrix_shp(tmp_path / "repro.shp")
        payload = _build_matrix_payload()
        rows_a = _run("run_a")
        rows_b = _run("run_b")
        assert len(rows_a) == len(rows_b) == 4

        def key(row):
            return (row["scheme"], row["attack"], row["trial"])

        for a, b in zip(sorted(rows_a, key=key), sorted(rows_b, key=key), strict=True):
            assert key(a) == key(b)
            assert a["attack_params"] == b["attack_params"], "same-seed sampling must be identical"
            assert a["decode_success"] == b["decode_success"]
            assert a["nc"] == pytest.approx(b["nc"], rel=1e-12) if a["nc"] is not None else True
            assert a["ber"] == pytest.approx(b["ber"], rel=1e-12) if a["ber"] is not None else True

        # Independently reproduce trial 1's translate draw: rng = default_rng(11+1),
        # first two draws are dx ~ U(0.003, 0.008), dy ~ U(0.002, 0.005).
        rng = np.random.default_rng(12)
        expected_dx = rng.uniform(0.003, 0.008)
        expected_dy = rng.uniform(0.002, 0.005)
        by_key = {key(row): row for row in rows_a}
        params = by_key[("dqim1", "translate", 1)]["attack_params"]
        assert params["dx"] == expected_dx
        assert params["dy"] == expected_dy

    def test_trials_one_keeps_documented_defaults(self, db, tmp_path):
        """trials=1 stays on the pre-trials path: documented default parameters."""
        from algorithm.robustness import run_matrix

        shp = _make_matrix_shp(tmp_path / "legacy_defaults.shp")
        rows = run_matrix(
            shp,
            None,
            schemes=["legacy"],
            attacks=["translate", "noise"],
            trials=1,
            payload_text=_build_matrix_payload(),
            work_dir=str(tmp_path / "work_defaults"),
        )
        by_attack = {row["attack"]: row for row in rows}
        assert by_attack["translate"]["attack_params"] == {"dx": 0.005, "dy": 0.003}
        assert by_attack["noise"]["attack_params"] == {"sigma": 1e-9}
        assert by_attack["translate"]["trial"] == 1


class TestSeededNoiseReproducibility:
    """Step 1b: the Gaussian attack is a pure function of (input, seed)."""

    @pytest.fixture
    def small_shp(self, tmp_path):
        import geopandas as gpd
        from shapely.geometry import LineString

        rng = np.random.default_rng(5)
        lines = [LineString(np.column_stack([np.arange(40) * 0.001, rng.uniform(0, 1, 40)])) for _ in range(2)]
        shp = str(tmp_path / "noise_src.shp")
        gpd.GeoDataFrame({"fid": range(2)}, geometry=lines, crs="EPSG:4326").to_file(shp)
        return shp

    def test_vector_noise_same_seed_byte_identical(self, small_shp, tmp_path):
        import geopandas as gpd

        from algorithm.robustness import attack_noise

        out1 = attack_noise(small_shp, sigma=1e-9, seed=21, output_path=str(tmp_path / "n21a.shp"))
        out2 = attack_noise(small_shp, sigma=1e-9, seed=21, output_path=str(tmp_path / "n21b.shp"))
        out3 = attack_noise(small_shp, sigma=1e-9, seed=22, output_path=str(tmp_path / "n22.shp"))
        g1 = gpd.read_file(out1)
        g2 = gpd.read_file(out2)
        g3 = gpd.read_file(out3)
        for a, b in zip(g1.geometry, g2.geometry, strict=True):
            assert np.asarray(a.coords).tobytes() == np.asarray(b.coords).tobytes()
        # A different seed must sample different noise (guards against an
        # unseeded/constant implementation sneaking back in).
        assert any(
            np.asarray(a.coords).tobytes() != np.asarray(b.coords).tobytes()
            for a, b in zip(g1.geometry, g3.geometry, strict=True)
        )

    def test_raster_noise_same_seed_byte_identical(self, tmp_path):
        from algorithm.robustness_raster import make_host_tif, r_noise

        host = make_host_tif(str(tmp_path / "host.tif"))
        out1 = r_noise(host, sigma=5.0, seed=31, output_path=str(tmp_path / "r31a.tif"))
        out2 = r_noise(host, sigma=5.0, seed=31, output_path=str(tmp_path / "r31b.tif"))
        out3 = r_noise(host, sigma=5.0, seed=32, output_path=str(tmp_path / "r32.tif"))

        import rasterio

        def _bytes(path):
            with rasterio.open(path) as src:
                return src.read().tobytes()

        assert _bytes(out1) == _bytes(out2), "same-seed raster noise must be byte-identical"
        assert _bytes(out1) != _bytes(out3), "different seeds must sample different noise"


# =========================================================================== #
# Raster engine — trials parameterization, per-trial hosts                    #
# =========================================================================== #


class TestRasterTrialsEngine:
    def _payload_qr(self, db, tmp_path):
        from algorithm.robustness_raster import render_raster_payload_qr

        qr_path = str(tmp_path / "payload_qr.png")
        text = _build_matrix_payload()
        render_raster_payload_qr(text, qr_path)
        return qr_path, text

    def test_trials_rows_params_and_host_seeds(self, db, tmp_path):
        import rasterio

        from algorithm.robustness_raster import make_host_tif, run_raster_matrix

        qr_path, _text = self._payload_qr(db, tmp_path)
        work = str(tmp_path / "work_raster_trials")
        rows = run_raster_matrix(None, ["lsb"], ["none", "jpeg", "noise"], qr_path, work, trials=2)
        assert len(rows) == 6
        per_attack = {}
        for row in rows:
            per_attack.setdefault(row["attack"], []).append(row["trial"])
            if row["attack"] == "jpeg":
                quality = row["attack_params"]["quality"]
                assert isinstance(quality, int) and 60 <= quality <= 80
            elif row["attack"] == "noise":
                assert 3.0 <= row["attack_params"]["sigma"] <= 8.0
                assert row["attack_params"]["seed"] == 11 + row["trial"]
        assert per_attack == {"none": [1, 2], "jpeg": [1, 2], "noise": [1, 2]}

        # Per-trial hosts exist and are the documented seed-t hosts (7 + trial).
        import os

        host_t1 = os.path.join(work, "host_t1.tif")
        host_t2 = os.path.join(work, "host_t2.tif")
        assert os.path.isfile(host_t1) and os.path.isfile(host_t2)

        def _data(path):
            with rasterio.open(path) as src:
                return src.read()

        with rasterio.open(make_host_tif(str(tmp_path / "expect_t1.tif"), seed=8)) as src:
            expect_t1 = src.read()
        with rasterio.open(make_host_tif(str(tmp_path / "expect_t2.tif"), seed=9)) as src:
            expect_t2 = src.read()
        assert np.array_equal(_data(host_t1), expect_t1), "trial 1 host must use seed 7+1"
        assert np.array_equal(_data(host_t2), expect_t2), "trial 2 host must use seed 7+2"
        assert not np.array_equal(expect_t1, expect_t2), "host seeds must actually vary"

    def test_raster_trials_reproducible(self, db, tmp_path):
        from algorithm.robustness_raster import run_raster_matrix

        qr_path, _text = self._payload_qr(db, tmp_path)

        def _run(tag):
            return run_raster_matrix(None, ["lsb"], ["none", "jpeg"], qr_path, str(tmp_path / tag), trials=2)

        rows_a = _run("a")
        rows_b = _run("b")

        def key(row):
            return (row["scheme"], row["attack"], row["trial"])

        assert len(rows_a) == len(rows_b) == 4
        for a, b in zip(sorted(rows_a, key=key), sorted(rows_b, key=key), strict=True):
            assert key(a) == key(b)
            assert a["attack_params"] == b["attack_params"]
            assert a["decode_success"] == b["decode_success"]

    def test_raster_trials_one_keeps_documented_defaults(self, db, tmp_path):
        from algorithm.robustness_raster import make_host_tif, run_raster_matrix

        qr_path, _text = self._payload_qr(db, tmp_path)
        host = make_host_tif(str(tmp_path / "host_single.tif"))
        rows = run_raster_matrix(host, ["lsb"], ["jpeg"], qr_path, str(tmp_path / "work_single"), trials=1)
        assert len(rows) == 1
        assert rows[0]["trial"] == 1
        assert rows[0]["attack_params"] == {"quality": 70}


# =========================================================================== #
# Endpoint — trials validation, totals, summary aggregation                   #
# =========================================================================== #


class TestTrialsEndpoint:
    @pytest.fixture
    def dataset_id(self, db, tmp_path):
        import uuid

        from model.Shp_Data import Shp

        # The test SQLite file keeps rows for the whole session, so the alias
        # (unique column) needs a per-instantiation suffix.
        uid = uuid.uuid4().hex[:8]
        shp_path = _make_matrix_shp(tmp_path / "trials_api_src.shp")
        record = Shp(
            name=f"trials_api_src_{uid}",
            alias=f"trials_api_src_{uid}",
            geomtype="LineString",
            introduction="trials endpoint smoke",
            shp_file_path=shp_path,
            coordinate_system="EPSG:4326",
        )
        db.session.add(record)
        db.session.commit()
        return record.id

    def test_trials_validation_rejects_out_of_range(self, client, db, auth_headers, dataset_id):
        base = {"data_id": dataset_id, "schemes": ["dqim1"], "attacks": ["none"]}
        for bad in (0, 11, -1, "2", None, True):
            resp = client.post("/api/robustness/run", json={**base, "trials": bad}, headers=auth_headers)
            if bad is None:
                # None is indistinguishable from "not provided" in JSON bodies;
                # the endpoint treats an explicit null as missing -> still valid.
                continue
            assert resp.status_code == 400, f"trials={bad!r} must be rejected, got {resp.status_code}"
            assert "trials" in resp.get_json()["msg"]

    def test_trials_validation_rejects_oversized_matrix(self, client, db, auth_headers):
        # Raster defaults are 5 schemes x 6 attacks = 30 cells; 30 x 10 = 300 > 200.
        resp = client.post("/api/robustness/run", json={"kind": "raster", "trials": 10}, headers=auth_headers)
        assert resp.status_code == 400
        assert "200" in resp.get_json()["msg"]

    def test_trials_run_total_rows_and_summary(self, client, db, auth_headers, dataset_id):
        resp = client.post(
            "/api/robustness/run",
            json={"data_id": dataset_id, "schemes": ["dqim1"], "attacks": ["none"], "trials": 2},
            headers=auth_headers,
        )
        assert resp.status_code == 202, resp.get_json()
        data = resp.get_json()["data"]
        assert data["total"] == 2, "response data.total must be the expected row count (cells x trials)"
        assert data["trials"] == 2
        run_id = data["run_id"]
        _join_worker(run_id)

        detail = client.get(f"/api/robustness/runs/{run_id}", headers=auth_headers).get_json()["run"]
        assert detail["trials"] == 2
        assert [row["trial"] for row in detail["rows"]] == [1, 2]
        summary = {(entry["scheme"], entry["attack"]): entry for entry in detail["summary"]}
        entry = summary[("dqim1", "none")]
        assert entry["trials"] == 2
        assert entry["successes"] == sum(1 for row in detail["rows"] if row["decode_success"])
        assert entry["success_rate"] == pytest.approx(entry["successes"] / 2)

        listing = client.get("/api/robustness/runs", headers=auth_headers).get_json()["runs"]
        listed = next(entry for entry in listing if entry["run_id"] == run_id)
        assert listed["trials"] == 2

    def test_raster_endpoint_trials_smoke(self, client, db, auth_headers):
        resp = client.post(
            "/api/robustness/run",
            json={"kind": "raster", "schemes": ["lsb"], "attacks": ["none"], "trials": 2},
            headers=auth_headers,
        )
        assert resp.status_code == 202, resp.get_json()
        run_id = resp.get_json()["data"]["run_id"]
        _join_worker(run_id)
        detail = client.get(f"/api/robustness/runs/{run_id}", headers=auth_headers).get_json()["run"]
        assert detail["trials"] == 2
        assert sorted(row["trial"] for row in detail["rows"]) == [1, 2]
        assert {row["decode_success"] for row in detail["rows"]} == {True}


class TestSummaryAggregationMath:
    """Hand-computed aggregation over crafted rows (no engine involved)."""

    @pytest.fixture
    def crafted_run(self, db):
        from model.robustness_result import RobustnessResult

        run_id = "test-summary-math"
        rows = [
            # dqim1 x none: 3 trials, 2 successes, ncs [0.9, 1.0] -> mean 0.95, popstd 0.05
            RobustnessResult(
                run_id=run_id, scheme="dqim1", attack="none", trial=1, decode_success=True, nc=0.9, ber=0.1
            ),
            RobustnessResult(
                run_id=run_id, scheme="dqim1", attack="none", trial=2, decode_success=True, nc=1.0, ber=0.0
            ),
            RobustnessResult(run_id=run_id, scheme="dqim1", attack="none", trial=3, decode_success=False, nc=None),
            # dqim1 x translate: 2 trials, all failed with null nc -> mean/std None
            RobustnessResult(run_id=run_id, scheme="dqim1", attack="translate", trial=1, decode_success=False, nc=None),
            RobustnessResult(run_id=run_id, scheme="dqim1", attack="translate", trial=2, decode_success=False, nc=None),
            # legacy x none: failed but nc present (decoded the wrong payload)
            # -> excluded from successes, included in mean/std (nc not null)
            RobustnessResult(run_id=run_id, scheme="legacy", attack="none", trial=1, decode_success=False, nc=0.4),
            # old-style row without trial (legacy data compatibility)
            RobustnessResult(
                run_id=run_id, scheme="legacy", attack="translate", trial=None, decode_success=True, nc=0.99
            ),
        ]
        db.session.add_all(rows)
        db.session.commit()
        return run_id

    def test_summary_math(self, client, db, auth_headers, crafted_run):
        detail = client.get(f"/api/robustness/runs/{crafted_run}", headers=auth_headers).get_json()["run"]
        assert detail["trials"] == 3
        by_cell = {(entry["scheme"], entry["attack"]): entry for entry in detail["summary"]}

        none = by_cell[("dqim1", "none")]
        assert none["trials"] == 3 and none["successes"] == 2
        assert none["success_rate"] == pytest.approx(2 / 3)
        assert none["mean_nc"] == pytest.approx(0.95)
        assert none["std_nc"] == pytest.approx(0.05)

        translate = by_cell[("dqim1", "translate")]
        assert translate["trials"] == 2 and translate["successes"] == 0
        assert translate["success_rate"] == 0.0
        assert translate["mean_nc"] is None and translate["std_nc"] is None

        legacy_none = by_cell[("legacy", "none")]
        assert legacy_none["trials"] == 1 and legacy_none["successes"] == 0
        assert legacy_none["mean_nc"] == pytest.approx(0.4)
        assert legacy_none["std_nc"] == pytest.approx(0.0)

        legacy_translate = by_cell[("legacy", "translate")]
        assert legacy_translate["trials"] == 1 and legacy_translate["successes"] == 1
        assert legacy_translate["mean_nc"] == pytest.approx(0.99)

        # Rows keep the trial field; a null trial (legacy row) survives the round trip.
        assert {row["trial"] for row in detail["rows"]} == {None, 1, 2, 3}


class TestZombieRunSweep:
    @pytest.fixture
    def dataset_id(self, db, tmp_path):
        from model.Shp_Data import Shp

        shp_path = _make_matrix_shp(tmp_path / "sweep_src.shp")
        record = Shp(
            name="sweep_src",
            alias="sweep_src",
            geomtype="LineString",
            introduction="zombie sweep fixture",
            shp_file_path=shp_path,
            coordinate_system="EPSG:4326",
        )
        db.session.add(record)
        db.session.commit()
        return record.id

    def test_start_run_sweeps_zombies_only(self, client, db, auth_headers, dataset_id):
        from model.robustness_result import RobustnessResult

        # 1) A zombie: every row pending, no error (worker died with the process).
        db.session.add_all(
            [
                RobustnessResult(run_id="zombie-run", scheme="dqim1", attack="none", trial=1),
                RobustnessResult(run_id="zombie-run", scheme="dqim1", attack="translate", trial=1),
            ]
        )
        # 2) A run that made progress must NOT be touched.
        db.session.add_all(
            [
                RobustnessResult(
                    run_id="partial-run", scheme="dqim1", attack="none", trial=1, decode_success=True, nc=0.99
                ),
                RobustnessResult(run_id="partial-run", scheme="dqim1", attack="translate", trial=1),
            ]
        )
        # 3) An already-stamped run keeps its original message.
        db.session.add(
            RobustnessResult(
                run_id="stamped-run",
                scheme="dqim1",
                attack="none",
                trial=1,
                error="interrupted by server restart",
            )
        )
        db.session.commit()

        resp = client.post(
            "/api/robustness/run",
            json={"data_id": dataset_id, "schemes": ["dqim1"], "attacks": ["none"], "trials": 1},
            headers=auth_headers,
        )
        assert resp.status_code == 202, resp.get_json()
        _join_worker(resp.get_json()["data"]["run_id"])
        db.session.expire_all()

        zombie_errors = {row.error for row in RobustnessResult.query.filter_by(run_id="zombie-run").all()}
        assert zombie_errors == {"interrupted (no active worker)"}

        partial_errors = {row.error for row in RobustnessResult.query.filter_by(run_id="partial-run").all()}
        assert partial_errors == {None}

        stamped = RobustnessResult.query.filter_by(run_id="stamped-run").first()
        assert stamped.error == "interrupted by server restart"

        # The runs list surfaces the zombie with an error and zero progress,
        # which the UI renders as the interrupted/error badge, not "running".
        listing = client.get("/api/robustness/runs", headers=auth_headers).get_json()["runs"]
        zombie = next(entry for entry in listing if entry["run_id"] == "zombie-run")
        assert zombie["error"] == "interrupted (no active worker)"
        assert zombie["done"] == 0 and zombie["total"] == 2
