from datetime import datetime
from extension.extension import db


class FriendRequest(db.Model):
    __bind_key__ = 'mysql_db'
    __tablename__ = 'friend_request'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    owner_number = db.Column(db.String(64), nullable=False, index=True)
    owner_role = db.Column(db.String(32), nullable=False, index=True)
    owner_name = db.Column(db.String(255), nullable=True)
    friend_number = db.Column(db.String(64), nullable=False, index=True)
    friend_role = db.Column(db.String(32), nullable=False, index=True)
    status = db.Column(db.String(16), nullable=False, default='pending', index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
