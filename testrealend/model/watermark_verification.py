from datetime import UTC, datetime

from extension.extension import db


class WatermarkVerification(db.Model):
    """Records each watermark comparison (original vs extracted) for forensic traceability."""

    __bind_key__ = "mysql_db"
    __tablename__ = "watermark_verification"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    application_id = db.Column(db.Integer, nullable=True)
    data_id = db.Column(db.Integer, nullable=True)
    data_type = db.Column(db.String(20), nullable=True)  # 'vector' or 'raster'
    nc_value = db.Column(db.Float, nullable=False)
    # Quality metrics beyond NC. All nullable: legacy rows (no source data to
    # backfill) and write paths that cannot produce a metric stay NULL.
    algorithm = db.Column(db.String(32), nullable=True)
    psnr = db.Column(db.Float, nullable=True)
    ssim = db.Column(db.Float, nullable=True)
    ber = db.Column(db.Float, nullable=True)
    # Optional v3 delivery linkage, read from optional upload form fields.
    delivery_uuid = db.Column(db.String(36), nullable=True)
    fingerprint_id = db.Column(db.String(32), nullable=True)
    host_type = db.Column(db.String(16), nullable=True)
    original_hash = db.Column(db.String(64), nullable=True)
    extracted_hash = db.Column(db.String(64), nullable=True)
    verified_by = db.Column(db.String(255), nullable=True)
    verified_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    ip_address = db.Column(db.String(255), nullable=True)

    __table_args__ = (
        # Serve the quality-page aggregation endpoints (filter by type/algorithm
        # over a time window).
        db.Index("idx_wmv_data_type_time", "data_type", "verified_at"),
        db.Index("idx_wmv_algorithm_time", "algorithm", "verified_at"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "application_id": self.application_id,
            "data_id": self.data_id,
            "data_type": self.data_type,
            "nc_value": self.nc_value,
            "algorithm": self.algorithm,
            "psnr": self.psnr,
            "ssim": self.ssim,
            "ber": self.ber,
            "delivery_uuid": self.delivery_uuid,
            "fingerprint_id": self.fingerprint_id,
            "host_type": self.host_type,
            "original_hash": self.original_hash,
            "extracted_hash": self.extracted_hash,
            "verified_by": self.verified_by,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "ip_address": self.ip_address,
        }
