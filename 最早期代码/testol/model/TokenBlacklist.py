from datetime import datetime
from zoneinfo import ZoneInfo
from extension.extension import db


class TokenBlacklist(db.Model):
    __bind_key__ = 'mysql_db'
    __tablename__ = 'token_blacklist'
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(tz=ZoneInfo("UTC")))
