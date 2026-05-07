from datetime import datetime
from extension.extension import db


class ChatMessage(db.Model):
    __bind_key__ = 'mysql_db'
    __tablename__ = 'chat_message'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sender_number = db.Column(db.String(64), nullable=False, index=True)
    sender_role = db.Column(db.String(32), nullable=False, index=True)
    receiver_number = db.Column(db.String(64), nullable=False, index=True)
    receiver_role = db.Column(db.String(32), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
