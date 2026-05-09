from extension.extension import db
from datetime import datetime, timezone


class WatermarkVerification(db.Model):
    """Records each watermark comparison (original vs extracted) for forensic traceability."""
    __bind_key__ = 'mysql_db'
    __tablename__ = 'watermark_verification'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    application_id = db.Column(db.Integer, nullable=True)
    data_id = db.Column(db.Integer, nullable=True)
    nc_value = db.Column(db.Float, nullable=False)
    original_hash = db.Column(db.String(64), nullable=True)
    extracted_hash = db.Column(db.String(64), nullable=True)
    verified_by = db.Column(db.String(255), nullable=True)
    verified_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    ip_address = db.Column(db.String(255), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'application_id': self.application_id,
            'data_id': self.data_id,
            'nc_value': self.nc_value,
            'original_hash': self.original_hash,
            'extracted_hash': self.extracted_hash,
            'verified_by': self.verified_by,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'ip_address': self.ip_address
        }
