from extension.extension import db
from datetime import datetime

class EmployeeInfo(db.Model):
    __bind_key__ = 'mysql_db'
    __tablename__ = 'employee_info'
    employee_number = db.Column(db.String(255), primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    job_number = db.Column(db.String(255), unique=True, nullable=False)
    id_number = db.Column(db.String(255), unique=True, nullable=False)
    phone_number = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=True)
    department = db.Column(db.String(255), nullable=True)
    address = db.Column(db.String(255), nullable=False)
    hire_date = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_time = db.Column(db.DateTime)
    create_time = db.Column(db.DateTime, default=datetime.utcnow)
    update_time = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    face_photo = db.Column(db.LargeBinary)
    avatar_path = db.Column(db.String(500), nullable=True)
