import uuid
from sqlalchemy.dialects.postgresql import UUID
from extension.extension import db
# from geoalchemy2 import Geometry # 正确地移除了

class Shp(db.Model):
    __bind_key__ = 'postgres_db'
    __tablename__ = 'shp_data'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=True)
    alias = db.Column(db.String(255), unique=True, nullable=True)
    geomtype = db.Column(db.String(255), nullable=False)
    introduction = db.Column(db.String(255), nullable=False)
    datetime = db.Column(db.DateTime, nullable=True)
    url = db.Column(db.String(255), nullable=True)
    layer = db.Column(db.String(255), nullable=True)
    shp_file_path = db.Column(db.String(255), nullable=False)
    uuid = db.Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    coordinate_system = db.Column(db.String(100), nullable=True)
    data_source = db.Column(db.String(255), nullable=True)

    def to_dict(self):
        # ==================== 主要修改点 ====================
        # 我们要确保返回的字典键名与前端 <el-table-column> 和 <el-descriptions-item>
        # 中使用的 prop 和变量名完全一致。
        return {
            # --- 基础字段 ---
            'data_id': self.id,
            'uuid': str(self.uuid) if self.uuid else None,
            'geomtype': self.geomtype,
            
            # --- 名称和简介 (核心修复) ---
            # 前端表格 prop="data_alias" 需要这个字段
            'data_alias': self.alias, 
            # 前端弹窗的详情部分需要这个字段
            'data_introduction': self.introduction,

            # --- WMS地图服务相关字段 ---
            # 前端 openMapDialog 函数需要这些字段
            'data_url': self.url,
            'layer': self.layer,

            # --- 其他可能用到的字段 (保留) ---
            'name': self.name,
            'alias': self.alias, # 保留 'alias' 以防万一
            'introduction': self.introduction, # 保留 'introduction'
            'datetime': self.datetime.isoformat() if self.datetime else None,
            'coordinate_system': self.coordinate_system,
            'data_source': self.data_source,
        }