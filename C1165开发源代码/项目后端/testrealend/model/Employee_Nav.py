from zoneinfo import ZoneInfo
from datetime import datetime
from extension.extension import db


class EmployeeNav(db.Model):
    __bind_key__ = 'mysql_db'
    __tablename__ = 'employee_nav'
    id = db.Column(db.Integer, primary_key=True, nullable=True)
    parent_id = db.Column(db.Integer, nullable=True)
    name = db.Column(db.String(255), nullable=True)
    path = db.Column(db.String(255), nullable=True)
    level = db.Column(db.Integer, nullable=True)
    sort = db.Column(db.Integer)
    status = db.Column(db.SmallInteger)
    create_time = db.Column(db.DateTime, default=datetime.now(tz=ZoneInfo("UTC")))
