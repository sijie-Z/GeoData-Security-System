from extension.extension import db


class ExtractHelper(db.Model):
    __bind_key__ = 'mysql_db'
    __tablename__ = 'ExtractHelper'
    id = db.Column(db.Integer, primary_key=True)
    data_id = db.Column(db.Integer, db.ForeignKey('data.id'))
    data_name = db.Column(db.String(255), unique=True, nullable=True)
    data_alias = db.Column(db.String(255), unique=True, nullable=True)
    geomtype = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(255), nullable=True)
    vr = db.Column(db.JSON, nullable=True)  # 使用 JSON 类型存储数组
