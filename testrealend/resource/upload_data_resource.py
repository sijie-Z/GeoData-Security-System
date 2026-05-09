import os
import zipfile
import logging

from flask import request, current_app
from flask_restful import Resource
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename
from datetime import datetime, timezone

from extension.extension import db, limiter
from model.Shp_Data import Shp
from model.Raster_Data import RasterData


def _safe_extract_zip(zip_ref, dest_dir):
    for member in zip_ref.namelist():
        target = os.path.realpath(os.path.join(dest_dir, member))
        if not target.startswith(os.path.realpath(dest_dir)):
            raise ValueError(f"非法文件路径: {member}")
    zip_ref.extractall(dest_dir)


class ShpDataUploadResource(Resource):
    @jwt_required()
    @limiter.limit("10 per minute")
    def post(self):
        data_alias = (request.form.get('data_alias') or '').strip()
        category = (request.form.get('category') or '').strip()
        data_introduction = (request.form.get('data_introduction') or '').strip()

        if not data_alias:
            return {'status': False, 'msg': '数据名称不能为空'}, 400

        if 'file' not in request.files:
            return {'status': False, 'msg': '未找到上传文件'}, 400

        file = request.files['file']
        if not file.filename or not file.filename.lower().endswith('.zip'):
            return {'status': False, 'msg': '仅支持 .zip 格式文件'}, 400

        try:
            filename = secure_filename(file.filename)
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'shp_uploads')
            os.makedirs(upload_dir, exist_ok=True)

            save_path = os.path.join(upload_dir, filename)
            file.save(save_path)

            extract_dir = os.path.join(upload_dir, os.path.splitext(filename)[0])
            os.makedirs(extract_dir, exist_ok=True)

            with zipfile.ZipFile(save_path, 'r') as zf:
                _safe_extract_zip(zf, extract_dir)

            shp_files = []
            for root, _, files in os.walk(extract_dir):
                for f in files:
                    if f.lower().endswith('.shp'):
                        shp_files.append(os.path.join(root, f))

            if len(shp_files) != 1:
                return {'status': False, 'msg': f'ZIP包中应包含且仅包含一个 .shp 文件，当前找到 {len(shp_files)} 个'}, 400

            shp_file_path = shp_files[0]
            geomtype = 'Unknown'
            coordinate_system = None
            layer_name = os.path.splitext(os.path.basename(shp_file_path))[0]

            try:
                import fiona
                with fiona.open(shp_file_path) as src:
                    if src.schema and src.schema.get('geometry'):
                        geomtype = src.schema['geometry']
                    if src.crs:
                        from pyproj import CRS
                        try:
                            coordinate_system = CRS.from_user_input(src.crs).to_string()
                        except Exception:
                            coordinate_system = str(src.crs)
            except Exception:
                logging.warning(f"无法读取SHP元数据: {shp_file_path}")

            record = Shp(
                name=layer_name,
                alias=data_alias,
                geomtype=geomtype,
                introduction=data_introduction or '暂无简介',
                datetime=datetime.now(timezone.utc),
                url='',
                layer=layer_name,
                shp_file_path=shp_file_path,
                coordinate_system=coordinate_system,
                data_source=category or '未分类',
            )
            db.session.add(record)
            db.session.commit()

            return {'status': True, 'msg': '数据上传成功', 'data': record.to_dict()}, 201

        except ValueError as e:
            return {'status': False, 'msg': str(e)}, 400
        except Exception as e:
            db.session.rollback()
            logging.error(str(e))
            return {'status': False, 'msg': '上传失败，请稍后重试'}, 500


class RasterDataUploadResource(Resource):
    @jwt_required()
    @limiter.limit("10 per minute")
    def post(self):
        data_alias = (request.form.get('data_alias') or '').strip()
        category = (request.form.get('category') or '').strip()
        data_introduction = (request.form.get('data_introduction') or '').strip()

        if not data_alias:
            return {'status': False, 'msg': '数据名称不能为空'}, 400

        if 'file' not in request.files:
            return {'status': False, 'msg': '未找到上传文件'}, 400

        file = request.files['file']
        allowed_ext = ('.tif', '.tiff', '.img', '.png', '.jpg', '.jpeg')
        if not file.filename or not any(file.filename.lower().endswith(e) for e in allowed_ext):
            return {'status': False, 'msg': '仅支持 TIFF/PNG/JPG 格式的栅格文件'}, 400

        try:
            filename = secure_filename(file.filename)
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'raster_uploads')
            os.makedirs(upload_dir, exist_ok=True)

            save_path = os.path.join(upload_dir, filename)
            file.save(save_path)

            bands = None
            resolution = None
            coordinate_system = None

            try:
                from osgeo import gdal
                ds = gdal.Open(save_path)
                if ds:
                    bands = ds.RasterCount
                    gt = ds.GetGeoTransform()
                    if gt:
                        resolution = f"{abs(gt[1]):.4f} x {abs(gt[5]):.4f}"
                    srs = ds.GetSpatialRef()
                    if srs:
                        coordinate_system = srs.GetAttrValue('AUTHORITY', 1) or srs.ExportToWkt()
                    ds = None
            except Exception:
                logging.warning(f"无法读取栅格元数据: {save_path}")

            record = RasterData(
                name=os.path.splitext(filename)[0],
                alias=data_alias,
                introduction=data_introduction or '暂无简介',
                datetime=datetime.now(timezone.utc),
                url='',
                layer='',
                raster_file_path=save_path,
                coordinate_system=coordinate_system,
                data_source=category or '未分类',
                band_count=bands,
                pixel_type=str(bands) if bands else None,
            )
            db.session.add(record)
            db.session.commit()

            return {'status': True, 'msg': '栅格数据上传成功', 'data': record.to_dict()}, 201

        except Exception as e:
            db.session.rollback()
            logging.error(str(e))
            return {'status': False, 'msg': '上传失败，请稍后重试'}, 500
