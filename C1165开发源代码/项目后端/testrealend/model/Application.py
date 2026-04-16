from zoneinfo import ZoneInfo
from datetime import datetime
from extension.extension import db


class Application(db.Model):
    __bind_key__ = 'mysql_db'
    __tablename__ = 'application'
    id = db.Column(db.Integer, primary_key=True)
    data_id = db.Column(db.Integer, nullable=False)
    data_name = db.Column(db.String(255), nullable=False)
    data_alias = db.Column(db.String(255), nullable=False)
    data_url = db.Column(db.String(500), nullable=False)
    applicant_name = db.Column(db.String(255), nullable=False)
    applicant_user_number = db.Column(db.String(255), nullable=False)
    reason = db.Column(db.String(5000), nullable=False)
    adm1_user_number = db.Column(db.String(255), nullable=True)
    adm1_name = db.Column(db.String(255), nullable=True)
    adm1_statu = db.Column(db.Boolean, nullable=True)
    adm1_approve_statu = db.Column(db.Boolean, nullable=True)
    adm2_user_number = db.Column(db.String(255), nullable=True)
    adm2_name = db.Column(db.String(255), nullable=True)
    adm2_statu = db.Column(db.Boolean, nullable=True)
    adm2_approve_statu = db.Column(db.Boolean, nullable=True)
    QRcode = db.Column(db.LargeBinary)
    application_submission_time = db.Column(db.DateTime, default=datetime.now(tz=ZoneInfo("UTC")))
    adm1_approval_time = db.Column(db.DateTime)
    adm2_approval_time = db.Column(db.DateTime)


