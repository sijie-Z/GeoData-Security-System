from geoalchemy2 import Geometry

from extension.extension import db


class Shp(db.Model):
    __bind_key__ = 'postgres_db'
    __tablename__ = 'ShpDataIO'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=True)
    alias = db.Column(db.String(255), unique=True, nullable=True)
    geomtype = db.Column(db.String(255), nullable=False)
    introduction = db.Column(db.String(255), nullable=False)
    datetime = db.Column(db.DateTime, nullable=True)
    url = db.Column(db.String(255), nullable=True)
    # GetCapabilities = db.Column(db.String(255), nullable=True)
    layer = db.Column(db.String(255), nullable=True)
    shp_file_path = db.Column(db.String(255), nullable=False)
    geometry = db.Column(Geometry('GEOMETRY'), nullable=False)
    uuid = db.Column(db.String(255), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'alias': self.alias,
            'geomtype': self.geomtype,
            'introduction': self.introduction,
            'datetime': self.datetime,
            'url': self.url,
            'uuid': self.uuid,
            # 'GetCapabilities': self.GetCapabilities,
            'layer': self.layer,
        }
