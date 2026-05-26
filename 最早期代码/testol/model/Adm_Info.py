from zoneinfo import ZoneInfo
from datetime import datetime
from extension.extension import db


class AdmInfo(db.Model):
    __bind_key__ = 'mysql_db'
    __tablename__ = 'adm_info'
    adm_number = db.Column(db.String(255), primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    job_number = db.Column(db.String(255), unique=True, nullable=False)
    id_number = db.Column(db.String(255), unique=True, nullable=False)
    phone_number = db.Column(db.String(255), unique=True, nullable=False)
    address = db.Column(db.String(255), nullable=False)
    create_time = db.Column(db.DateTime, default=datetime.now(tz=ZoneInfo("UTC")))
    update_time = db.Column(db.DateTime, default=datetime.now(tz=ZoneInfo("UTC")),
                            onupdate=lambda: datetime.now(tz=ZoneInfo("UTC")))
    face_photo = db.Column(db.LargeBinary)
