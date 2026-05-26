from extension.extension import db
from zoneinfo import ZoneInfo
from datetime import datetime


class AdmLoginCheck(db.Model):
    __bind_key__ = 'mysql_db'
    __tablename__ = 'Adm_Login_Check'
    id = db.Column(db.Integer, primary_key=True)
    job_number = db.Column(db.String(255), db.ForeignKey('Adm_Info.job_number'), nullable=False)
    adm_number = db.Column(db.String(255), db.ForeignKey('Adm_Info.adm_number'), nullable=False)
    admin_info = db.relationship('AdmInfo', backref=db.backref('checks', lazy='dynamic'),
                                 primaryjoin="and_(AdmLoginCheck.job_number == AdmInfo.job_number, "
                                             "AdmLoginCheck.adm_number == AdmInfo.adm_number)")  # 双向关联
    adm_token = db.Column(db.String(255), nullable=False, unique=True)
    last_login = db.Column(db.DateTime, default=datetime.now(tz=ZoneInfo("UTC")))
