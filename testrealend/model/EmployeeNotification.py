from datetime import datetime, timezone
from extension.extension import db


class EmployeeNotification(db.Model):
    __bind_key__ = 'mysql_db'
    __tablename__ = 'employee_notification'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_number = db.Column(db.String(64), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    sender_number = db.Column(db.String(64), nullable=True)
    sender_name = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_number': self.user_number,
            'title': self.title,
            'content': self.content,
            'read': self.read,
            'sender_number': self.sender_number,
            'sender_name': self.sender_name,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }
