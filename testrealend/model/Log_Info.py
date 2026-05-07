from extension.extension import db
from datetime import datetime

class LogInfo(db.Model):
    __bind_key__ = 'mysql_db'
    __tablename__ = 'log_info'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_number = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(255), nullable=False)
    ip_address = db.Column(db.String(255), nullable=True)
    action = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), nullable=False) # '成功' or '失败'
    details = db.Column(db.Text, nullable=True)

    __table_args__ = (
        db.Index('idx_log_user_number', 'user_number'),
        db.Index('idx_log_action', 'action'),
        db.Index('idx_log_timestamp', 'timestamp'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.timestamp else None,
            'user_number': self.user_number,
            'username': self.username,
            'ip_address': self.ip_address,
            'action': self.action,
            'status': self.status,
            'details': self.details
        }
