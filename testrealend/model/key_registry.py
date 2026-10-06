from datetime import UTC, datetime

from extension.extension import db


class KeyRegistry(db.Model):
    """Registry of Ed25519 signing keys. Public material only — private keys never enter the DB."""

    __bind_key__ = "mysql_db"
    __tablename__ = "key_registry"

    kid = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(64), nullable=True)
    public_key = db.Column(db.LargeBinary(32), nullable=True)
    status = db.Column(db.String(16), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    revoked_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "kid": self.kid,
            "name": self.name,
            "public_key": bytes(self.public_key).hex() if self.public_key else None,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
        }
