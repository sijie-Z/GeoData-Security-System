from extension.extension import db
from zoneinfo import ZoneInfo
from datetime import datetime


class EmployeeLoginCheck(db.Model):
    __bind_key__ = 'mysql_db'
    __tablename__ = 'Employee_Login_Check'
    id = db.Column(db.Integer, primary_key=True)
    job_number = db.Column(db.String(255), db.ForeignKey('Employee_Info.job_number'), nullable=False)
    employee_number = db.Column(db.String(255), db.ForeignKey('Employee_Info.employee_number'), nullable=False)
    employee_info = db.relationship('EmployeeInfo', backref=db.backref('checks', lazy='dynamic'),
                                    primaryjoin="and_(EmployeeLoginCheck.job_number == EmployeeInfo.job_number, "  # 双向关联
                                                "EmployeeLoginCheck.employee_number == EmployeeInfo.employee_number)")
    employee_token = db.Column(db.String(255), nullable=False, unique=True)
    last_login = db.Column(db.DateTime, default=datetime.now(tz=ZoneInfo("UTC")))
