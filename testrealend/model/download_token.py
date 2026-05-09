from extension.extension import db
from datetime import datetime, timezone
import secrets


class DownloadToken(db.Model):
    """One-time-use download token for secure file distribution."""
    __bind_key__ = 'mysql_db'
    __tablename__ = 'download_token'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    application_id = db.Column(db.Integer, nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(32))
    user_number = db.Column(db.String(255), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'application_id': self.application_id,
            'token': self.token,
            'user_number': self.user_number,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_used': self.is_used,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
