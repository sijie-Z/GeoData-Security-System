from zoneinfo import ZoneInfo
from datetime import datetime
from extension.extension import db


class AdmAccount(db.Model):
    __bind_key__ = 'mysql_db'
    __tablename__ = 'adm_account'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    adm_user_name = db.Column(db.String(255), nullable=False)
    adm_user_password = db.Column(db.String(255), nullable=False)
    create_time = db.Column(db.DateTime, default=datetime.now(tz=ZoneInfo("UTC")))
    adm_number = db.Column(db.String(255), db.ForeignKey('adm_info.adm_number'), nullable=False)
