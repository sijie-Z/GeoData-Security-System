import uuid
from sqlalchemy.dialects.postgresql import UUID
from extension.extension import db
from datetime import datetime, timezone

class RasterData(db.Model):
    """
    栅格数据模型，用于在数据库中存储栅格文件的元数据。
    """
    __tablename__ = 'raster_data'
    __bind_key__ = 'postgres_db'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=True)
    alias = db.Column(db.String(255), nullable=True)

    # 栅格数据特有字段
    band_count = db.Column(db.Integer)
    pixel_type = db.Column(db.String(255))

    # 通用字段
    introduction = db.Column(db.String(255))
    datetime = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    url = db.Column(db.String(255))
    layer = db.Column(db.String(255))
    raster_file_path = db.Column(db.String(512))
    uuid = db.Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    coordinate_system = db.Column(db.String(100))
    data_source = db.Column(db.String(255))

    def to_dict(self):
        """
        将模型对象转换为字典格式。
        """
        return {
            'data_id': self.id,
            'uuid': str(self.uuid) if self.uuid else None,
            'data_alias': self.alias,
            'data_introduction': self.introduction,
            'data_url': self.url,
            'layer': self.layer,
            'name': self.name,
            'datetime': self.datetime.isoformat() if self.datetime else None,
            'coordinate_system': self.coordinate_system,
            'data_source': self.data_source,
            'band_count': self.band_count,
            'pixel_type': self.pixel_type
        }
