from extension.extension import db


class MysqlShpFile(db.Model):
    __bind_key__ = 'mysql_db'
    __tablename__ = 'MysqlShpIO'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=True)
    alias = db.Column(db.String(255), unique=True, nullable=True)
    geomtype = db.Column(db.String(255), nullable=False)
    introduction = db.Column(db.String(255), nullable=False)
    datetime = db.Column(db.DateTime, nullable=True)
    url = db.Column(db.String(255), nullable=True)
    layer = db.Column(db.String(255), nullable=True)
    shp_file_path = db.Column(db.String(255), nullable=False)
