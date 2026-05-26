from extension.extension import db
from zoneinfo import ZoneInfo
from datetime import datetime
from model.Employee_Info import EmployeeInfo


class EmployeeAccount(db.Model):
    __bind_key__ = 'mysql_db'
    __tablename__ = 'employee_account'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    employee_user_name = db.Column(db.String(255), nullable=False)
    employee_user_password = db.Column(db.String(255), nullable=False)
    create_time = db.Column(db.DateTime, default=datetime.now(tz=ZoneInfo("UTC")))
    update_time = db.Column(db.DateTime, default=datetime.now(tz=ZoneInfo("UTC")),
                            onupdate=lambda: datetime.now(tz=ZoneInfo("UTC")))
    employee_number = db.Column(db.String(255), db.ForeignKey('employee_info.employee_number'), nullable=False)
