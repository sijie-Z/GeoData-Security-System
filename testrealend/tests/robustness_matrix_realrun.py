"""Real-machine robustness matrix run — direct engine call, read-only databases.

Runs ``algorithm.robustness.run_matrix`` inside this worktree (no HTTP, no
main-backend restart) against the source shapefile of one dataset row:

  * the shp path is resolved read-only from the live Postgres ``shp_data``
    table (same precedence as the delivery flow: ``shp_file_path`` then
    ``url``; ``--shp`` overrides);
  * the payload is a real v2 COSE payload signed with the live active key when
    ``--key-pem`` is given — the kid is matched read-only against the live
    MySQL ``key_registry`` by public-key bytes; without ``--key-pem`` a
    plain-text payload is used;
  * the live databases are ONLY read (SELECT): nothing is ever written back,
    and the running backend is untouched.

Usage (from testrealend):
    python tests/robustness_matrix_realrun.py --data-id 17 \
        --key-pem D:/path/to/main/testrealend/instance/keys/ed25519_active.pem \
        --json matrix.json
"""

import argparse
import os
import shutil
import sys
import tempfile
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
os.chdir(BASE_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, ".env"))

from config import Config

SHP_COMPONENT_EXTS = (".shp", ".shx", ".dbf", ".prj", ".cpg", ".qix")


def _load_shp_row(data_id):
    """Read-only lookup of the dataset row in the live Postgres shp_data table."""
    from sqlalchemy import create_engine, text

    engine = create_engine(Config.SQLALCHEMY_BINDS["postgres_db"])
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, name, alias, geomtype, shp_file_path, url FROM shp_data WHERE id = :i"),
            {"i": data_id},
        ).fetchone()
    return dict(row._mapping) if row else None


def _resolve_existing_path(path_value):
    """Same precedence/rewrite rules as delivery.service._resolve_existing_path,
    minus the Flask current_app dependency (root = this testrealend)."""
    if not path_value:
        return None
    candidate = str(path_value).replace("\\", "/").strip()
    if candidate.startswith("file://"):
        candidate = candidate[7:]
    if os.path.exists(candidate):
        return os.path.abspath(candidate)
    if candidate.startswith("/"):
        local = os.path.join(os.path.dirname(BASE_DIR), candidate.lstrip("/"))
        if os.path.exists(local):
            return os.path.abspath(local)
    local = os.path.join(BASE_DIR, candidate.lstrip("/"))
    if os.path.exists(local):
        return os.path.abspath(local)
    return None


def _live_kid_for(private_key):
    """Read-only lookup of the live kid whose public key matches this key."""
    from cryptography.hazmat.primitives import serialization
    from sqlalchemy import create_engine, text

    pub_raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
    engine = create_engine(Config.SQLALCHEMY_BINDS["mysql_db"])
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT kid, public_key FROM key_registry ORDER BY kid")).fetchall()
    for kid, pub in rows:
        if pub is not None and bytes(pub) == pub_raw:
            return kid
    return None


def _load_private_key(pem_path):
    from cryptography.hazmat.primitives import serialization

    with open(pem_path, "rb") as fh:
        return serialization.load_pem_private_key(fh.read(), password=None)


def _build_payload_text(args):
    """Real v2 signed payload when a live key is available, else plain text."""
    if not args.key_pem:
        print("payload: plain-text (no --key-pem given)")
        return "ROBUSTNESS-REALRUN-PLAIN-PAYLOAD"
    private_key = _load_private_key(args.key_pem)
    kid = _live_kid_for(private_key)
    if kid is None:
        print("payload: WARN live key_registry has no row for this key — falling back to plain text")
        return "ROBUSTNESS-REALRUN-PLAIN-PAYLOAD"
    import base64
    from datetime import UTC, datetime

    from crypto import canonical
    from crypto.cose import sign1_sign
    from crypto.payload import V2_PREFIX

    fid_hex = os.urandom(16).hex()
    issued_at = int(datetime.now(UTC).timestamp())
    payload_cbor = canonical.dumps(
        {"v": 2, "kid": kid, "fid": bytes.fromhex(fid_hex), "delivery": args.data_id, "issued_at": issued_at}
    )
    cose = sign1_sign(payload_cbor, kid, private_key)
    text = V2_PREFIX + base64.urlsafe_b64encode(cose).rstrip(b"=").decode()
    print(f"payload: v2 COSE (kid={kid}, fid={fid_hex[:8]}…, {len(text)} chars)")
    return text


def _stage_source(shp_path, work_root):
    """Copy the source shapefile + companions under the work dir (never write next to the original)."""
    stage_dir = os.path.join(work_root, "source")
    os.makedirs(stage_dir, exist_ok=True)
    base = os.path.splitext(shp_path)[0]
    for ext in SHP_COMPONENT_EXTS:
        src = base + ext
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(stage_dir, os.path.basename(src)))
    return os.path.join(stage_dir, os.path.basename(shp_path))


def _vertex_count(shp_path):
    import geopandas as gpd
    from shapely import get_num_coordinates

    gdf = gpd.read_file(shp_path)
    return int(get_num_coordinates(gdf.geometry.values).sum())


def main():
    sys.stdout.reconfigure(line_buffering=True)  # long runs: keep progress visible when redirected
    parser = argparse.ArgumentParser(description="Real-machine robustness matrix (read-only DBs)")
    parser.add_argument("--data-id", type=int, default=17, help="shp_data.id (the E2E dataset row is 17)")
    parser.add_argument("--shp", default=None, help="override the source .shp path (skips the DB lookup)")
    parser.add_argument("--key-pem", default=None, help="live Ed25519 private key (PEM) for a real v2 payload")
    parser.add_argument("--scheme", action="append", default=None, help="restrict schemes (repeatable)")
    parser.add_argument("--attack", action="append", default=None, help="restrict attacks (repeatable)")
    parser.add_argument("--work-dir", default=None, help="work dir (default: fresh temp dir)")
    parser.add_argument("--keep-work", action="store_true", help="keep the self-created temp work dir")
    parser.add_argument("--json", default=None, help="dump the full matrix as JSON to this path")
    args = parser.parse_args()

    if args.shp:
        shp_path = os.path.abspath(args.shp)
        print(f"source: --shp override {shp_path}")
    else:
        row = _load_shp_row(args.data_id)
        if row is None:
            sys.exit(f"shp_data id={args.data_id} not found in the live Postgres database")
        print(
            "dataset: id={id} name={name!r} alias={alias!r} geomtype={geomtype}".format(
                id=row["id"], name=row["name"], alias=row["alias"], geomtype=row["geomtype"]
            )
        )
        shp_path = _resolve_existing_path(row["shp_file_path"]) or _resolve_existing_path(row["url"])
        if not shp_path:
            sys.exit(
                f"shp_data id={args.data_id}: no on-disk source file "
                f"(shp_file_path={row['shp_file_path']!r} url={row['url']!r})"
            )
    if not os.path.isfile(shp_path):
        sys.exit(f"source file missing on disk: {shp_path}")
    print(f"source: {shp_path} ({os.path.getsize(shp_path) / 1e6:.2f} MB)")

    payload_text = _build_payload_text(args)

    own_work_dir = args.work_dir is None
    work_root = args.work_dir or tempfile.mkdtemp(prefix=f"robustness_real_{args.data_id}_")
    print(f"work dir: {work_root}")
    staged = _stage_source(shp_path, work_root)
    print(f"vertices: {_vertex_count(staged)}")

    from algorithm.robustness import ATTACKS, SCHEMES, run_matrix

    schemes = args.scheme or list(SCHEMES)
    attacks = args.attack or list(ATTACKS)
    print(f"matrix: schemes={schemes} attacks={attacks}")

    started = time.time()
    rows = run_matrix(staged, None, schemes=schemes, attacks=attacks, payload_text=payload_text, work_dir=work_root)
    elapsed = time.time() - started

    header = f"{'scheme':8s} {'attack':12s} {'ok':>4s} {'nc':>8s} {'ber':>8s} {'ms':>10s}  error"
    print("\n" + header)
    print("-" * len(header))
    for row in rows:
        ok = "-" if row["decode_success"] is None else ("PASS" if row["decode_success"] else "FAIL")
        nc = "-" if row["nc"] is None else f"{row['nc']:.4f}"
        ber = "-" if row["ber"] is None else f"{row['ber']:.4f}"
        ms = "-" if row["duration_ms"] is None else str(row["duration_ms"])
        print(f"{row['scheme']:8s} {row['attack']:12s} {ok:>4s} {nc:>8s} {ber:>8s} {ms:>10s}  {row['error'] or ''}")
    print(f"\ntotal wall time: {elapsed:.1f}s")

    if args.json:
        import json

        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "data_id": args.data_id,
                    "source_shp": shp_path,
                    "staged_shp": staged,
                    "payload_chars": len(payload_text),
                    "schemes": schemes,
                    "attacks": attacks,
                    "elapsed_s": round(elapsed, 1),
                    "rows": rows,
                },
                fh,
                ensure_ascii=False,
                indent=2,
            )
        print(f"json: {args.json}")

    if own_work_dir and not args.keep_work:
        shutil.rmtree(work_root, ignore_errors=True)
        print("work dir cleaned (use --keep-work to keep artifacts)")


if __name__ == "__main__":
    main()
