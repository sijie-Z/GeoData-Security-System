from extension.extension import db


class EmbedFileRecord(db.Model):
    __bind_key__ = 'mysql_db'
    __tablename__ = 'Embed_File_Record'
    id = db.Column(db.Integer, primary_key=True)
    data_id = db.Column(db.Integer, unique=False, nullable=False)
    application_id = db.Column(db.Integer, unique=False, nullable=False)
    generate_filename = db.Column(db.String(500), unique=True, nullable=False)
    generate_file_path = db.Column(db.String(500), unique=True, nullable=False)
    embed_person = db.Column(db.String(500), unique=False, nullable=False)
    applicant = db.Column(db.String(500), unique=False, nullable=False)
    embed_time = db.Column(db.DateTime, nullable=False)
    vr = db.Column(db.JSON, nullable=True)
