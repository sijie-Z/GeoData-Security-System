from extension.extension import db


class DownloadFileRecord(db.Model):
    __bind_key__ = 'mysql_db'
    __tablename__ = 'Download_File_Record'
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, unique=False, nullable=False)
    data_id = db.Column(db.Integer, unique=False, nullable=False)
    Send_file_person = db.Column(db.String(255), nullable=False)
    Download_File_Name = db.Column(db.String(255), nullable=False)
    Download_File_Person = db.Column(db.String(255), nullable=False)
    Download_Time = db.Column(db.DateTime)

