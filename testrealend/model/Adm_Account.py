from extension.extension import db
from datetime import datetime, timezone

class AdmAccount(db.Model):
    __bind_key__ = 'mysql_db'
    __tablename__ = 'adm_account'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    adm_user_name = db.Column(db.String(255), nullable=False)
    adm_user_password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False) # admin1, admin2, admin3
    create_time = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    adm_number = db.Column(db.String(255), db.ForeignKey('adm_info.adm_number'), nullable=False)
