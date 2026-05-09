from extension.extension import db
from datetime import datetime, timezone

class AdmInfo(db.Model):
    __bind_key__ = 'mysql_db'
    __tablename__ = 'adm_info'
    adm_number = db.Column(db.String(255), primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    job_number = db.Column(db.String(255), unique=True, nullable=False)
    id_number = db.Column(db.String(255), unique=True, nullable=False)
    phone_number = db.Column(db.String(255), unique=True, nullable=False)
    address = db.Column(db.String(255), nullable=False)
    last_login_time = db.Column(db.DateTime)
    create_time = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    update_time = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    face_photo = db.Column(db.LargeBinary)
