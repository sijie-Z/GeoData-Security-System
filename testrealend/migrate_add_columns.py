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
    "ALTER TABLE download_record ADD COLUMN applicant_user_number VARCHAR(255) NULL",
    "ALTER TABLE download_record ADD COLUMN filename VARCHAR(255) NULL",
    "ALTER TABLE download_record ADD COLUMN timestamp DATETIME NULL",
    "ALTER TABLE employee_info ADD COLUMN email VARCHAR(255) NULL",
    "ALTER TABLE employee_info ADD COLUMN department VARCHAR(255) NULL",
    "ALTER TABLE employee_info ADD COLUMN hire_date DATETIME NULL",
    "ALTER TABLE employee_info ADD COLUMN last_login_time DATETIME NULL",
    "ALTER TABLE employee_info ADD COLUMN avatar_path VARCHAR(500) NULL",
    "ALTER TABLE employee_nav ADD COLUMN icon VARCHAR(255) NULL",
]


def run():
    app = create_app()
    with app.app_context():
        mysql_engine = db.get_engine(bind='mysql_db')
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
                    if 'Duplicate column' in err:
                        skip += 1
                        print(f"  [SKIP] already exists")
                    else:
                        fail += 1
                        print(f"  [FAIL] {err[:60]}")

        print(f"\nDone. {ok} added, {skip} already existed, {fail} failed.")


if __name__ == '__main__':
    run()
