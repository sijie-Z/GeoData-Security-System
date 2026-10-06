"""Benchmark result DB layer: idempotent JSON import, /api/benchmark/stats
structure + JSON-compatible row keys, and the legacy file endpoint reading the
moved (non-web-exposed) JSON.
"""

import copy
import json
import os

import pytest

from config import BASE_DIR
from model.benchmark_result import BenchmarkResult
from tests.import_benchmark_results import DEFAULT_JSON, import_results, run_id_for

PAYLOAD = {
    "benchmark_metadata": {"timestamp": "2026-06-01T10:00:00"},
    "results": [
        {
            "algorithm": "LSB",
            "host_type": "natural",
            "embed_time": 0.5,
            "embed_success": True,
            "stego_psnr": 51.1,
            "stego_ssim": 0.999,
            "baseline_nc": 1.0,
            "baseline_ber": 0.0,
            "recovery_psnr": 999.0,
            "recovery_perfect": True,
            "wm_bit_count": 3400,
        },
        {
            "algorithm": "LSB",
            "host_type": "natural",
            "attack": "JPEG q=90",
            "attack_type": "jpeg",
            "attack_params": {"quality": 90},
            "nc": 0.99,
            "ber": 0.01,
            "decode_success": True,
            "decode_error": None,
            "recovery_psnr": 55.5,
            "recovery_perfect": False,
        },
    ],
}


@pytest.fixture(autouse=True)
def _clean_benchmark_rows(db):
    """Committed rows persist across tests in the shared file-backed test DB."""
    BenchmarkResult.query.delete()
    db.session.commit()
    yield


class TestImport:
    def test_import_is_idempotent(self, db):
        first = import_results(PAYLOAD)
        assert first["imported"] == 2 and first["skipped_existing"] == 0
        second = import_results(copy.deepcopy(PAYLOAD))
        assert second["imported"] == 0 and second["skipped_existing"] == 2
        assert BenchmarkResult.query.count() == 2
        kinds = {row.kind for row in BenchmarkResult.query.all()}
        assert kinds == {"summary", "attack"}

    def test_missing_timestamp_rejected(self, db):
        with pytest.raises(ValueError):
            import_results({"results": []})

    def test_failure_row_classified(self, db):
        payload = {
            "benchmark_metadata": {"timestamp": "2026-06-03T10:00:00"},
            "results": [{"algorithm": "Histogram", "embed_error": "boom", "embed_success": False}],
        }
        import_results(payload)
        row = BenchmarkResult.query.one()
        assert row.kind == "failure" and row.embed_error == "boom"
        assert row.to_dict()["embed_success"] is False


class TestBenchmarkStatsEndpoint:
    def test_real_file_roundtrip_and_compat_keys(self, db, client, auth_headers):
        with open(DEFAULT_JSON, encoding="utf-8") as f:
            payload = json.load(f)
        summary = import_results(payload)

        resp = client.get("/api/benchmark/stats", headers=auth_headers)
        assert resp.status_code == 200, resp.get_json()
        body = resp.get_json()
        assert body["status"] is True
        assert body["latest_run"]["run_id"] == summary["run_id"]
        assert body["latest_run"]["created_at"]
        assert body["runs_count"] == 1
        assert len(body["results"]) == len(payload["results"]) == 49

        expected_summaries = [r for r in payload["results"] if "stego_psnr" in r]
        expected_attacks = [r for r in payload["results"] if "attack" in r]
        expected_failures = [
            r for r in payload["results"] if "attack" not in r and "stego_psnr" not in r
        ]  # the Histogram embed failure in the 2026-05-15 snapshot
        got_summaries = [r for r in body["results"] if "stego_psnr" in r]
        got_attacks = [r for r in body["results"] if "attack" in r]
        got_failures = [r for r in body["results"] if "attack" not in r and "stego_psnr" not in r]
        assert len(got_summaries) == len(expected_summaries)
        assert len(got_attacks) == len(expected_attacks)
        assert len(got_failures) == len(expected_failures) == 1
        assert got_failures[0]["embed_error"] == expected_failures[0]["embed_error"]
        assert len(got_summaries) + len(got_attacks) + len(got_failures) == len(payload["results"])

        # rows are discriminated and parsed exactly like the JSON file rows
        assert got_summaries[0]["algorithm"] == expected_summaries[0]["algorithm"]
        assert got_summaries[0]["stego_psnr"] == expected_summaries[0]["stego_psnr"]
        exp_attack = next(r for r in payload["results"] if "attack" in r)
        for key in ("algorithm", "attack", "attack_type", "attack_params", "nc", "ber", "decode_success"):
            assert got_attacks[0][key] == exp_attack[key], key

    def test_latest_run_and_runs_count(self, db, client, auth_headers):
        p1 = copy.deepcopy(PAYLOAD)
        p2 = copy.deepcopy(PAYLOAD)
        p2["benchmark_metadata"]["timestamp"] = "2026-07-01T09:00:00"
        import_results(p1)
        import_results(p2)
        body = client.get("/api/benchmark/stats", headers=auth_headers).get_json()
        assert body["runs_count"] == 2
        assert body["latest_run"]["run_id"] == run_id_for("2026-07-01T09:00:00")
        assert len(body["results"]) == 2

    def test_empty_state(self, db, client, auth_headers):
        body = client.get("/api/benchmark/stats", headers=auth_headers).get_json()
        assert body == {"status": True, "latest_run": None, "runs_count": 0, "results": []}

    def test_employee_forbidden(self, db, client, employee_headers):
        resp = client.get("/api/benchmark/stats", headers=employee_headers)
        assert resp.status_code == 403


class TestLegacyEndpoint:
    def test_reads_moved_json_and_static_path_is_gone(self, db, client, employee_headers):
        old_static = os.path.join(BASE_DIR, "static", "benchmark_results", "robustness_benchmark.json")
        assert not os.path.exists(old_static), "benchmark JSON must not live under static/ (web-exposed)"
        assert os.path.exists(DEFAULT_JSON)

        resp = client.get("/api/benchmark/results", headers=employee_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["status"] is True
        assert len(body["data"]["results"]) == 49
        assert "benchmark_metadata" in body["data"]
