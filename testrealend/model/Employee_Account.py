from extension.extension import db
from datetime import datetime, timezone

class EmployeeAccount(db.Model):
    __bind_key__ = 'mysql_db'
    __tablename__ = 'employee_account'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    employee_user_name = db.Column(db.String(255), nullable=False, unique=True)
    employee_user_password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='employee')
    create_time = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    update_time = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    employee_number = db.Column(db.String(255), db.ForeignKey('employee_info.employee_number'), nullable=False)

    __table_args__ = (
        db.Index('idx_emp_account_number', 'employee_number'),
        db.Index('idx_emp_account_role', 'role'),
    )
