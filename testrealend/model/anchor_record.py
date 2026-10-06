from datetime import UTC, datetime

from extension.extension import db


class AnchorRecord(db.Model):
    """OpenTimestamps anchor record for the merkle root of an evidence batch."""

    __bind_key__ = "mysql_db"
    __tablename__ = "anchor_record"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    batch_id = db.Column(db.String(36), unique=True)
    root_hex = db.Column(db.String(64))
    provider = db.Column(db.String(32))
    status = db.Column(db.String(16), default="PENDING")
    proof_path = db.Column(db.String(512), nullable=True)
    error = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
