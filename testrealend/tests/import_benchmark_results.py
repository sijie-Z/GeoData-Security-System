"""Import robustness benchmark results (JSON) into the ``benchmark_result`` table.

One JSON payload becomes one run: ``run_id`` is derived deterministically from
``benchmark_metadata.timestamp`` (uuid5), so importing the same file twice is a
no-op (idempotent) instead of duplicating rows.

The JSON used to live under ``static/benchmark_results/`` — a web-exposed path
served without authentication. It now lives in ``data/benchmark_results/``
(``DEFAULT_JSON``); run this script after ``tests/benchmark_all_algorithms.py``
regenerates it:

    python tests/import_benchmark_results.py [path/to/robustness_benchmark.json]
"""

import json
import os
import sys
import uuid
from datetime import UTC, datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from extension.extension import db
from model.benchmark_result import BenchmarkResult

DEFAULT_JSON = os.path.join(PROJECT_ROOT, "data", "benchmark_results", "robustness_benchmark.json")


def run_id_for(timestamp):
    """Deterministic 36-char run id from the benchmark timestamp."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"robustness_benchmark:{timestamp}"))


def _parse_ts(timestamp):
    try:
        dt = datetime.fromisoformat(timestamp)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC).replace(tzinfo=None)
    return dt


def _row_from_result(result, run_id, created_at):
    """Map one JSON ``results`` entry to a BenchmarkResult (kind-dependent fields)."""
    row = BenchmarkResult(run_id=run_id, created_at=created_at)
    row.algorithm = result.get("algorithm")
    row.host_type = result.get("host_type")
    if "attack" in result:
        row.kind = "attack"
        row.attack = result.get("attack")
        row.attack_type = result.get("attack_type")
        row.attack_params = result.get("attack_params")
        row.nc = result.get("nc")
        row.ber = result.get("ber")
        row.decode_success = result.get("decode_success")
        decode_error = result.get("decode_error")
        row.decode_error = str(decode_error)[:255] if decode_error else None
        row.recovery_psnr = result.get("recovery_psnr")
        row.recovery_perfect = result.get("recovery_perfect")
    elif "stego_psnr" in result:
        row.kind = "summary"
        row.embed_time = result.get("embed_time")
        row.embed_success = result.get("embed_success")
        row.stego_psnr = result.get("stego_psnr")
        row.stego_ssim = result.get("stego_ssim")
        row.baseline_nc = result.get("baseline_nc")
        row.baseline_ber = result.get("baseline_ber")
        row.recovery_psnr = result.get("recovery_psnr")
        row.recovery_perfect = result.get("recovery_perfect")
        row.wm_bit_count = result.get("wm_bit_count")
    else:
        row.kind = "failure"
        row.embed_success = result.get("embed_success", False)
        row.embed_error = (result.get("embed_error") or "")[:255] or None
    return row


def import_results(payload, session=None):
    """Idempotently import one benchmark payload. Returns an import summary dict.

    A payload whose derived run_id is already present is skipped entirely, so
    re-running the import never duplicates rows.
    """
    session = session or db.session
    timestamp = (payload.get("benchmark_metadata") or {}).get("timestamp")
    if not timestamp:
        raise ValueError("benchmark payload is missing benchmark_metadata.timestamp")
    run_id = run_id_for(timestamp)
    existing = session.query(BenchmarkResult).filter_by(run_id=run_id).count()
    if existing:
        return {"run_id": run_id, "imported": 0, "skipped_existing": existing}

    created_at = _parse_ts(timestamp) or datetime.now(UTC)
    results = payload.get("results") or []
    for result in results:
        session.add(_row_from_result(result, run_id, created_at))
    session.commit()
    return {"run_id": run_id, "imported": len(results), "skipped_existing": 0}


def main():
    import importlib.util

    json_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_JSON
    with open(json_path, encoding="utf-8") as f:
        payload = json.load(f)

    # Importlib keeps the standalone `myapp` name from colliding with any
    # installed `app` package (same pattern as generate_verification_records.py).
    spec = importlib.util.spec_from_file_location("myapp", os.path.join(PROJECT_ROOT, "app.py"))
    app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_module)
    app = app_module.create_app()

    with app.app_context():
        summary = import_results(payload)
    print(f"json: {json_path}")
    print(f"run_id={summary['run_id']} imported={summary['imported']} skipped_existing={summary['skipped_existing']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
