from extension.extension import db
from datetime import datetime

class Announcement(db.Model):
    __bind_key__ = 'mysql_db'
    __tablename__ = 'announcement'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    tag = db.Column(db.String(64), nullable=True, default='重要')
    tag_color = db.Column(db.String(32), nullable=True, default='#F59E0B')
    icon = db.Column(db.String(64), nullable=True, default='InfoFilled')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    author_id = db.Column(db.String(255), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'tag': self.tag,
            'tag_color': self.tag_color,
            'icon': self.icon,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'author_id': self.author_id
        }
