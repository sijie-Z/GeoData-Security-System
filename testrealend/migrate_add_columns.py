"""
One-time migration script to add missing columns.
"""

import os

if os.name == "nt":
    import platform

    platform.machine = lambda: os.environ.get("PROCESSOR_ARCHITECTURE", "AMD64")

from app import create_app
from extension.extension import db

MYSQL_ALTERS = [
    "ALTER TABLE adm_info ADD COLUMN last_login_time DATETIME NULL",
    "ALTER TABLE adm_nav ADD COLUMN icon VARCHAR(255) NULL",
    "ALTER TABLE application ADD COLUMN watermark_generated TINYINT(1) DEFAULT 0",
    "ALTER TABLE application ADD COLUMN watermark_embedded TINYINT(1) DEFAULT 0",
    "ALTER TABLE application ADD COLUMN qrcode TEXT NULL",
    "ALTER TABLE application ADD COLUMN watermark_path VARCHAR(500) NULL",
    "ALTER TABLE application ADD COLUMN vr_data TEXT NULL",
    # Fix TEXT truncation for QR code and vector data columns
    "ALTER TABLE application MODIFY COLUMN qrcode MEDIUMTEXT NULL",
    "ALTER TABLE application MODIFY COLUMN vr_data MEDIUMTEXT NULL",
    # Blind watermark payload source: the v1 QR text behind `qrcode` (the blind
    # dispatch re-renders it at box_size=1 for its ~one-bit-per-64-pixels
    # budget). Nullable; legacy rows stay NULL and get a "重新生成水印" 400.
    "ALTER TABLE application ADD COLUMN qr_text TEXT NULL",
    "ALTER TABLE download_record ADD COLUMN applicant_user_number VARCHAR(255) NULL",
    "ALTER TABLE download_record ADD COLUMN filename VARCHAR(255) NULL",
    "ALTER TABLE download_record ADD COLUMN timestamp DATETIME NULL",
    "ALTER TABLE employee_info ADD COLUMN email VARCHAR(255) NULL",
    "ALTER TABLE employee_info ADD COLUMN department VARCHAR(255) NULL",
    "ALTER TABLE employee_info ADD COLUMN hire_date DATETIME NULL",
    "ALTER TABLE employee_info ADD COLUMN last_login_time DATETIME NULL",
    "ALTER TABLE employee_info ADD COLUMN avatar_path VARCHAR(500) NULL",
    "ALTER TABLE employee_nav ADD COLUMN icon VARCHAR(255) NULL",
    "ALTER TABLE application ADD COLUMN adm1_comment TEXT NULL",
    "ALTER TABLE application ADD COLUMN adm2_comment TEXT NULL",
    # v3 delivery core: link existing download records/tokens to the new
    # download_delivery table. The new tables themselves (download_delivery /
    # key_registry / evidence_event / anchor_record / benchmark_result) are
    # created automatically by _bootstrap_runtime_schema()'s registered
    # create_all — no ALTER needed.
    "ALTER TABLE download_token ADD COLUMN delivery_id BIGINT NULL",
    "ALTER TABLE download_record ADD COLUMN delivery_id BIGINT NULL",
    # B-6: existing environments that already created download_delivery before
    # these columns were added. New databases are covered by create_all.
    "ALTER TABLE download_delivery ADD COLUMN vr_data TEXT NULL",
    "ALTER TABLE download_delivery ADD COLUMN artifact_meta_path VARCHAR(512) NULL",
    # C-2/E-3: anchor completeness binding + proof digest for tables created by
    # an earlier v3 build (idempotent, "Duplicate column" rows are skipped).
    "ALTER TABLE anchor_record ADD COLUMN event_count INTEGER NULL",
    "ALTER TABLE anchor_record ADD COLUMN head_hash VARCHAR(64) NULL",
    "ALTER TABLE anchor_record ADD COLUMN proof_sha256 VARCHAR(64) NULL",
    # Watermark quality metrics + optional v3 linkage for verification records.
    # All nullable; legacy rows stay NULL (no source data to backfill).
    "ALTER TABLE watermark_verification ADD COLUMN algorithm VARCHAR(32) NULL",
    "ALTER TABLE watermark_verification ADD COLUMN psnr FLOAT NULL",
    "ALTER TABLE watermark_verification ADD COLUMN ssim FLOAT NULL",
    "ALTER TABLE watermark_verification ADD COLUMN ber FLOAT NULL",
    "ALTER TABLE watermark_verification ADD COLUMN delivery_uuid VARCHAR(36) NULL",
    "ALTER TABLE watermark_verification ADD COLUMN fingerprint_id VARCHAR(32) NULL",
    "ALTER TABLE watermark_verification ADD COLUMN host_type VARCHAR(16) NULL",
    # feat_experiment_trials: per-trial rows for multi-trial robustness runs.
    # NULL on legacy rows = single-trial run (the API derives trials=1).
    "ALTER TABLE robustness_result ADD COLUMN trial INT NULL",
    # feat_strength_sweep: 0-4 intensity tier of a sweep row; NULL = matrix row
    # (the API derives the run mode from this NULL-ness).
    "ALTER TABLE robustness_result ADD COLUMN strength_index INT NULL",
    # Indexes backing the quality-page aggregation endpoints; an existing index
    # name is skipped like a duplicate column (see run()).
    "CREATE INDEX idx_wmv_data_type_time ON watermark_verification (data_type, verified_at)",
    "CREATE INDEX idx_wmv_algorithm_time ON watermark_verification (algorithm, verified_at)",
    # 波 6 · backend-perf: indexes for the high-traffic download/audit filters
    # (dashboard date windows, per-application lookups, per-user statistics).
    # New databases get them from the models' index=True via create_all; this
    # block upgrades existing MySQL databases. Names match SQLAlchemy's default
    # ix_<table>_<column> convention so both paths converge.
    "CREATE INDEX ix_download_record_timestamp ON download_record (timestamp)",
    "CREATE INDEX ix_download_record_application_id ON download_record (application_id)",
    "CREATE INDEX ix_download_record_download_user_number ON download_record (download_user_number)",
    "CREATE INDEX ix_download_record_data_id ON download_record (data_id)",
    "CREATE INDEX ix_download_token_application_id ON download_token (application_id)",
    "CREATE INDEX ix_embed_file_record_application_id ON embed_file_record (application_id)",
    "CREATE INDEX ix_send_file_record_application_id ON send_file_record (application_id)",
]


def run():
    app = create_app()
    with app.app_context():
        mysql_engine = db.get_engine(bind="mysql_db")
        ok = 0
        skip = 0
        fail = 0

        with mysql_engine.connect() as conn:
            for sql in MYSQL_ALTERS:
                try:
                    conn.execute(db.text(sql))
                    conn.commit()
                    ok += 1
                    print(f"  [OK] {sql[:70]}")
                except Exception as e:
                    conn.rollback()
                    err = str(e)
                    # Idempotent re-run: columns ("Duplicate column"), MySQL
                    # indexes ("Duplicate key name") and SQLite indexes
                    # ("index ... already exists") are not failures.
                    if "Duplicate column" in err or "Duplicate key name" in err or "already exists" in err.lower():
                        skip += 1
                        print("  [SKIP] already exists")
                    else:
                        fail += 1
                        print(f"  [FAIL] {err[:60]}")

        print(f"\nDone. {ok} added, {skip} already existed, {fail} failed.")


if __name__ == "__main__":
    run()
