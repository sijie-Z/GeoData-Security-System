import uuid
from datetime import UTC, datetime

from extension.extension import db


class DownloadDelivery(db.Model):
    """v3 delivery pipeline record for signed (COSE/Ed25519) dataset downloads."""

    __bind_key__ = "mysql_db"
    __tablename__ = "download_delivery"

    delivery_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    application_id = db.Column(db.Integer, nullable=False)
    data_id = db.Column(db.Integer, nullable=False)
    data_type = db.Column(db.String(16), nullable=True)
    user_number = db.Column(db.String(64), nullable=True)
    fingerprint_id = db.Column(db.String(32), nullable=False)
    status = db.Column(db.String(16), default="PENDING")
    algorithm = db.Column(db.String(32), nullable=True)
    artifact_path = db.Column(db.String(512), nullable=True)
    artifact_root = db.Column(db.String(64), nullable=True)
    error = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    ready_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.Index("idx_delivery_app_user", "application_id", "user_number"),
        db.Index("idx_delivery_status", "status"),
    )

    def to_dict(self):
        return {
            "delivery_id": self.delivery_id,
            "uuid": self.uuid,
            "application_id": self.application_id,
            "data_id": self.data_id,
            "data_type": self.data_type,
            "user_number": self.user_number,
            "fingerprint_id": self.fingerprint_id,
            "status": self.status,
            "algorithm": self.algorithm,
            "artifact_path": self.artifact_path,
            "artifact_root": self.artifact_root,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "ready_at": self.ready_at.isoformat() if self.ready_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
