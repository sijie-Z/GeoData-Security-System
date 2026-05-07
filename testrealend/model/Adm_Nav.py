from datetime import datetime
from extension.extension import db

class AdmNav(db.Model):
    __bind_key__ = 'mysql_db'
    __tablename__ = 'adm_nav'
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, nullable=True)
    name = db.Column(db.String(255), nullable=True)
    path = db.Column(db.String(255), nullable=True)
    icon = db.Column(db.String(255), nullable=True)
    level = db.Column(db.Integer, nullable=True)
    sort = db.Column(db.Integer)
    status = db.Column(db.SmallInteger)
    create_time = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'parent_id': self.parent_id,
            'name': self.name,
            'path': self.path,
            'icon': self.icon,
            'level': self.level,
            'sort': self.sort,
            'status': self.status
        }
