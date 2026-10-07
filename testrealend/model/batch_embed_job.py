"""Batch watermark-embed job models (feat_batch_embed).

A ``BatchEmbedJob`` is one async batch activity over up to 50 application ids:
the endpoint answers immediately with the job uuid and a background daemon
thread walks the pre-inserted ``BatchEmbedItem`` rows, running every
application through the exact single-embed dispatch
(``resource.watermark_embed_resource.dispatch_embed_application``) — algorithm
dispatch, blind compact-QR channel and honest capacity errors included.

Job ``status`` ∈ queued/running/done; ``error`` carries a short summary for a
job that died with the process (stamped ``ZOMBIE_ERROR_MESSAGE`` by the next
submission's sweep, see ``resource/batch_embed_resource.py``) or aborted.
Item ``status`` ∈ pending/ok/fail with the per-item error truncated to 500
chars. Tables are created by ``_bootstrap_runtime_schema()`` (app.py) via
``create_all`` on fresh installs; no additive-column migration needed.
"""

from datetime import UTC, datetime

from extension.extension import db
from utils.time_fmt import utc_iso_z


class BatchEmbedJob(db.Model):
    __bind_key__ = "mysql_db"
    __tablename__ = "batch_embed_job"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), unique=True, index=True, nullable=False)
    status = db.Column(db.String(16), nullable=False, default="queued")  # queued / running / done
    algorithm = db.Column(db.String(32), nullable=False, default="lsb")
    total = db.Column(db.Integer, nullable=False, default=0)
    done = db.Column(db.Integer, nullable=False, default=0)
    ok = db.Column(db.Integer, nullable=False, default=0)
    fail = db.Column(db.Integer, nullable=False, default=0)
    created_by = db.Column(db.String(255), nullable=True)  # admin user_number from the JWT
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)
    # Touched at creation, per-item start and per-item completion; a
    # queued/running job untouched for 10 minutes is a zombie (its worker died
    # with the process) and the next submission sweeps it.
    updated_at = db.Column(db.DateTime, nullable=True)
    error = db.Column(db.String(255), nullable=True)

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "status": self.status,
            "algorithm": self.algorithm,
            "total": self.total,
            "done": self.done,
            "ok": self.ok,
            "fail": self.fail,
            "created_by": self.created_by,
            "created_at": utc_iso_z(self.created_at),
            "started_at": utc_iso_z(self.started_at),
            "finished_at": utc_iso_z(self.finished_at),
            "error": self.error,
        }


class BatchEmbedItem(db.Model):
    __bind_key__ = "mysql_db"
    __tablename__ = "batch_embed_item"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    job_id = db.Column(db.Integer, db.ForeignKey("batch_embed_job.id"), index=True, nullable=False)
    application_id = db.Column(db.Integer, nullable=False)
    data_id = db.Column(db.Integer, nullable=True)  # snapshot for the result table
    data_type = db.Column(db.String(50), nullable=True)  # raster / vector (audit action naming)
    status = db.Column(db.String(16), nullable=False, default="pending")  # pending / ok / fail
    error = db.Column(db.String(500), nullable=True)
    updated_at = db.Column(db.DateTime, nullable=True)
