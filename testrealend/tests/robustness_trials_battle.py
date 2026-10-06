"""Multi-trial (trials) real-machine battle — direct engine call, read-only DBs.

Runs the trials-augmented robustness matrices inside this worktree (no HTTP,
no main-backend restart, no run lock held — the live backend is untouched) and
aggregates every cell into success rate + mean/std NC:

  * vector battle: source shapefile of one live dataset row (default
    ``data_id=17``, read-only lookup in the live Postgres ``shp_data`` table),
    ``2 schemes x 6 attacks x trials=5 = 60 rows``;
  * raster battle: synthetic 512x512 host per trial (production
    ``kind="raster"`` parity, host seed varies with the trial),
    ``4 schemes x 6 attacks x trials=3 = 72 rows``.

Payload: a real v2 COSE payload signed with the live active key when
``--key-pem`` is given (kid matched read-only against the live MySQL
``key_registry``); without it a plain-text payload is used. The live databases
are ONLY read (SELECT) — nothing is written back.

The complete aggregate JSON (rows + per-cell summary + timing) is dumped to
``--json`` (a %%TEMP%% path is recommended).

Usage (from testrealend):
    python tests/robustness_trials_battle.py \
        --key-pem D:/path/to/main/testrealend/instance/keys/ed25519_active.pem \
        --json %TEMP%/robustness_trials_battle.json
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from datetime import UTC, datetime
from statistics import mean, pstdev
from types import SimpleNamespace

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
os.chdir(BASE_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, ".env"))

# Same guard the backend applies at import (resource/raster_resource.py): the
# user-level PROJ_LIB exported by the PostgreSQL/PostGIS installer points at an
# ancient proj.db that breaks every rasterio/geopandas CRS lookup. Must run
# before rasterio/pyproj read the environment.
from resource.raster_resource import _ensure_proj_data_env

_ensure_proj_data_env()

from tests.robustness_matrix_realrun import (
    _build_payload_text,
    _load_shp_row,
    _resolve_existing_path,
    _stage_source,
    _vertex_count,
)

VECTOR_TRIALS_DEFAULT = 5
RASTER_TRIALS_DEFAULT = 3


def _aggregate(rows):
    """Per-(scheme, attack) success rate + mean/std of non-null NCs (population std).

    NC null (decode failed outright) is excluded from mean/std, mirroring the
    API summary block; all-null cells report ``None`` for both.
    """
    buckets = {}
    for row in rows:
        key = (row["scheme"], row["attack"])
        bucket = buckets.setdefault(
            key, {"scheme": row["scheme"], "attack": row["attack"], "trials": 0, "successes": 0, "errors": 0, "ncs": []}
        )
        bucket["trials"] += 1
        if row["decode_success"]:
            bucket["successes"] += 1
        if row.get("error"):
            bucket["errors"] += 1
        if row["nc"] is not None:
            bucket["ncs"].append(float(row["nc"]))
    summary = []
    for bucket in buckets.values():
        ncs = bucket["ncs"]
        summary.append(
            {
                "scheme": bucket["scheme"],
                "attack": bucket["attack"],
                "trials": bucket["trials"],
                "successes": bucket["successes"],
                "success_rate": round(bucket["successes"] / bucket["trials"], 4) if bucket["trials"] else None,
                "mean_nc": round(mean(ncs), 6) if ncs else None,
                "std_nc": round(pstdev(ncs), 6) if ncs else None,
                "error_rows": bucket["errors"],
            }
        )
    return summary


def _print_table(title, summary, elapsed_s, total_rows):
    schemes = list(dict.fromkeys(entry["scheme"] for entry in summary))
    attacks = list(dict.fromkeys(entry["attack"] for entry in summary))
    cells = {(entry["scheme"], entry["attack"]): entry for entry in summary}
    width = max(len(a) for a in attacks) + 2

    print(f"\n=== {title} — {total_rows} rows in {elapsed_s:.1f}s ===")
    header = f"{'scheme':10s}" + "".join(f"{a:>{width}s}" for a in attacks)
    print(header)
    print("-" * len(header))
    for scheme in schemes:
        line = f"{scheme:10s}"
        for attack in attacks:
            entry = cells.get((scheme, attack))
            if entry is None:
                line += f"{'-':>{width}s}"
                continue
            rate = f"{entry['successes']}/{entry['trials']}"
            if entry["mean_nc"] is None:
                text = f"{rate} —"
            else:
                text = f"{rate} {entry['mean_nc']:.3f}±{entry['std_nc']:.3f}"
            if entry["error_rows"]:
                text += "!"
            line += f"{text:>{width}s}"
        print(line)
    print("(cell = successes/trials  mean±std NC; '!' = some rows carry an engine error)")


def _run_vector_battle(args):
    from algorithm.robustness import ATTACKS, SCHEMES, run_matrix

    if args.shp:
        shp_path = os.path.abspath(args.shp)
        data_id = None
        print(f"[vector] source: --shp override {shp_path}")
    else:
        row = _load_shp_row(args.data_id)
        if row is None:
            sys.exit(f"[vector] shp_data id={args.data_id} not found in the live Postgres database")
        shp_path = _resolve_existing_path(row["shp_file_path"]) or _resolve_existing_path(row["url"])
        if not shp_path:
            sys.exit(f"[vector] shp_data id={args.data_id}: no on-disk source file")
        data_id = args.data_id
        print(f"[vector] dataset id={row['id']} name={row['name']!r} alias={row['alias']!r}")
    if not os.path.isfile(shp_path):
        sys.exit(f"[vector] source file missing on disk: {shp_path}")
    print(f"[vector] source: {shp_path} ({os.path.getsize(shp_path) / 1e6:.2f} MB)")

    payload_text = _build_payload_text(SimpleNamespace(key_pem=args.key_pem, data_id=data_id or 17))

    work_root = tempfile.mkdtemp(prefix=f"trials_battle_vector_{data_id or 'shp'}_")
    staged = _stage_source(shp_path, work_root)
    print(f"[vector] work dir: {work_root}; vertices: {_vertex_count(staged)}")

    started = time.time()
    rows = run_matrix(
        staged,
        None,
        schemes=list(SCHEMES),
        attacks=list(ATTACKS),
        trials=args.vector_trials,
        payload_text=payload_text,
        work_dir=work_root,
    )
    elapsed = time.time() - started

    shutil.rmtree(work_root, ignore_errors=True)
    return {
        "name": "vector",
        "data_id": data_id,
        "source_shp": shp_path,
        "trials": args.vector_trials,
        "schemes": list(SCHEMES),
        "attacks": list(ATTACKS),
        "elapsed_s": round(elapsed, 1),
        "rows": rows,
        "summary": _aggregate(rows),
    }


def _run_raster_battle(args):
    from algorithm.robustness_raster import render_raster_payload_qr, run_raster_matrix
    from resource.robustness_resource import RASTER_DEFAULT_ATTACKS

    payload_text = _build_payload_text(SimpleNamespace(key_pem=args.key_pem, data_id=0))

    work_root = tempfile.mkdtemp(prefix="trials_battle_raster_")
    payload_qr = os.path.join(work_root, "payload_qr.png")
    _png, side = render_raster_payload_qr(payload_text, payload_qr)
    print(f"[raster] work dir: {work_root}; payload QR {side}x{side}px; fill={args.raster_fill!r}")

    started = time.time()
    rows = run_raster_matrix(
        None if args.raster_trials > 1 else os.path.join(work_root, "host_512x512.tif"),
        None,
        list(RASTER_DEFAULT_ATTACKS),
        payload_qr,
        work_root,
        trials=args.raster_trials,
        host_fill=args.raster_fill,
    )
    elapsed = time.time() - started

    shutil.rmtree(work_root, ignore_errors=True)
    return {
        "name": "raster",
        "data_ref": "synthetic_512x512",
        "trials": args.raster_trials,
        "host_fill": args.raster_fill,
        "schemes": ["lsb", "dwt", "histogram", "blind"],
        "attacks": list(RASTER_DEFAULT_ATTACKS),
        "elapsed_s": round(elapsed, 1),
        "rows": rows,
        "summary": _aggregate(rows),
    }


def main():
    sys.stdout.reconfigure(line_buffering=True)  # long runs: keep progress visible when redirected
    parser = argparse.ArgumentParser(description="Multi-trial robustness battle (read-only DBs)")
    parser.add_argument("--vector", action="store_true", help="run only the vector battle")
    parser.add_argument("--raster", action="store_true", help="run only the raster battle")
    parser.add_argument("--data-id", type=int, default=17, help="shp_data.id for the vector battle")
    parser.add_argument("--shp", default=None, help="override the vector source .shp path")
    parser.add_argument("--key-pem", default=None, help="live Ed25519 private key (PEM) for a real v2 payload")
    parser.add_argument("--vector-trials", type=int, default=VECTOR_TRIALS_DEFAULT)
    parser.add_argument("--raster-trials", type=int, default=RASTER_TRIALS_DEFAULT)
    parser.add_argument(
        "--raster-fill",
        type=int,
        default=None,
        help="constant fill for the per-trial synthetic hosts (None = production-parity random host)",
    )
    parser.add_argument("--json", default=None, help="dump the full battle as JSON to this path")
    args = parser.parse_args()

    battles = []
    if args.vector or not args.raster:
        battles.append(_run_vector_battle(args))
    if args.raster or not args.vector:
        battles.append(_run_raster_battle(args))

    total_rows = 0
    for battle in battles:
        total_rows += len(battle["rows"])
        _print_table(
            f"{battle['name']} battle (trials={battle['trials']})",
            battle["summary"],
            battle["elapsed_s"],
            len(battle["rows"]),
        )
    print(f"\nTOTAL rows: {total_rows}")

    if args.json:
        payload = {
            "generated_at": datetime.now(UTC).isoformat(),
            "worktree": BASE_DIR,
            "key_pem": args.key_pem,
            "total_rows": total_rows,
            "battles": battles,
        }
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        print(f"json: {args.json}")

    if not args.vector and not args.raster and total_rows < 100:
        sys.exit(f"combined battle produced only {total_rows} rows (<100) — investigate before reporting")


if __name__ == "__main__":
    main()
