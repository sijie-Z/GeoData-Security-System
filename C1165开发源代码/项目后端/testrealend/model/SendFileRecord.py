from extension.extension import db


class SendFileRecord(db.Model):
    __bind_key__ = 'mysql_db'
    __tablename__ = 'Send_File_Record'
    id = db.Column(db.Integer, primary_key=True)
    data_id = db.Column(db.Integer, unique=False, nullable=False)
    application_id = db.Column(db.Integer, unique=False, nullable=False)
    file_path = db.Column(db.String(255), unique=True, nullable=False)
    filename = db.Column(db.String(255), unique=True, nullable=False)
    send_person = db.Column(db.String(255), unique=False, nullable=False)
    applicant = db.Column(db.String(255), unique=False, nullable=False)
    send_time = db.Column(db.DateTime, nullable=False)
    vr = db.Column(db.JSON, nullable=True)





