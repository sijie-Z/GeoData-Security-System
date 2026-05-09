from extension.extension import db
from datetime import datetime, timezone

class DownloadRecord(db.Model):
    __bind_key__ = 'mysql_db'
    __tablename__ = 'download_record'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    application_id = db.Column(db.Integer, nullable=True)
    data_id = db.Column(db.Integer, nullable=False)
    data_name = db.Column(db.String(255), nullable=False, default='')
    download_user_number = db.Column(db.String(255), nullable=False)
    download_time = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    download_ip = db.Column(db.String(255), nullable=True)
    applicant_user_number = db.Column(db.String(255), nullable=True)
    filename = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
