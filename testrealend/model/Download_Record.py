from datetime import UTC, datetime

from extension.extension import db


class DownloadRecord(db.Model):
    __bind_key__ = "mysql_db"
    __tablename__ = "download_record"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # High-traffic dashboard/forensics filters: timestamp (date windows),
    # application_id / data_id (per-application lookups) and the downloader
    # number (per-user statistics).
    application_id = db.Column(db.Integer, nullable=True, index=True)
    delivery_id = db.Column(db.Integer, nullable=True)
    data_id = db.Column(db.Integer, nullable=False, index=True)
    data_name = db.Column(db.String(255), nullable=False, default="")
    download_user_number = db.Column(db.String(255), nullable=False, index=True)
    download_time = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    download_ip = db.Column(db.String(255), nullable=True)
    applicant_user_number = db.Column(db.String(255), nullable=True)
    filename = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(UTC), index=True)
