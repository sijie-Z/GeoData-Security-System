from extension.extension import db


class ExtractHelper(db.Model):
    __bind_key__ = "mysql_db"
    __tablename__ = "extract_helper"
    id = db.Column(db.Integer, primary_key=True)
    # dangling legacy FK: the declared target table "data" exists in no bind
    # ("data" is defined in no MetaData; the raster_data/shp_data models are bound
    # to postgres_db), so the reference could never resolve and it poisoned
    # metadata.sorted_tables. No FK constraint for data_id ever existed in the
    # physical MySQL schema either (extract_helper_ibfk_1 covers application_id).
    # Degraded to a plain column.
    data_id = db.Column(db.Integer, nullable=True)
    data_name = db.Column(db.String(255), unique=True, nullable=True)
    data_alias = db.Column(db.String(255), unique=True, nullable=True)
    geomtype = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(255), nullable=True)
    vr = db.Column(db.JSON, nullable=True)  # 使用 JSON 类型存储数组
