import logging
import os
import shutil
import threading
import zipfile
from datetime import UTC, datetime

from flask import current_app, request
from flask_jwt_extended import jwt_required
from flask_restful import Resource
from werkzeug.utils import secure_filename

from extension.extension import db, limiter
from model.Raster_Data import RasterData
from model.Shp_Data import Shp
from utils.ai_config import _chat_completions_url, _get_ai_config, _get_ai_timeout
from utils.required import admin_required


def _bg_publish_geoserver(file_path, layer_name, data_type, record_id, model_class, app):
    """Background: publish file to GeoServer and update DB with WMS URL."""
    try:
        from utils.geoserver_utils import publish_geotiff, publish_shapefile

        if data_type == "shp":
            result = publish_shapefile(file_path, layer_name)
        else:
            result = publish_geotiff(file_path, layer_name)

        if result["success"]:
            with app.app_context():
                record = model_class.query.get(record_id)
                if record:
                    record.url = result["wms_url"]
                    record.layer = result["layer"]
                    db.session.commit()
                    logging.info(
                        "GeoServer published: id=%s layer=%s wms=%s",
                        record_id,
                        result["layer"],
                        result["wms_url"],
                    )
        else:
            logging.warning("GeoServer publish failed for %s: %s", layer_name, result.get("error"))
    except Exception as e:
        logging.warning("Background GeoServer publish error for %s: %s", layer_name, e)


def _extract_raster_metadata(file_path):
    """Extract raster metadata using GDAL or rasterio. Returns dict."""
    meta = {"bands": 0, "pixel_type": None, "resolution": None, "coordinate_system": None, "file_size": 0}
    try:
        meta["file_size"] = os.path.getsize(file_path)
    except Exception:
        pass

    # Try GDAL first
    try:
        from osgeo import gdal

        ds = gdal.Open(file_path)
        if ds:
            meta["bands"] = ds.RasterCount
            # Get actual pixel type from first band
            band = ds.GetRasterBand(1)
            if band:
                dtype_code = band.DataType
                meta["pixel_type"] = gdal.GetDataTypeName(dtype_code)
            gt = ds.GetGeoTransform()
            if gt and gt[1] != 0:
                meta["resolution"] = f"{abs(gt[1]):.6f} x {abs(gt[5]):.6f}"
            srs = ds.GetSpatialRef()
            if srs:
                auth_code = srs.GetAttrValue("AUTHORITY", 1)
                meta["coordinate_system"] = f"EPSG:{auth_code}" if auth_code else srs.ExportToWkt()[:95]
            ds = None
            return meta
    except ImportError:
        pass
    except Exception as e:
        logging.warning("GDAL metadata extraction failed: %s", e)

    # Fallback to rasterio
    try:
        import rasterio

        with rasterio.open(file_path) as src:
            meta["bands"] = src.count
            # Real pixel type (e.g. uint8, uint16, float32)
            meta["pixel_type"] = str(src.dtypes[0]) if src.dtypes else None
            if src.res and src.res[0] > 0:
                meta["resolution"] = f"{src.res[0]:.6f} x {src.res[1]:.6f}"
            if src.crs:
                try:
                    epsg = src.crs.to_epsg()
                    meta["coordinate_system"] = f"EPSG:{epsg}" if epsg else str(src.crs)[:95]
                except Exception:
                    meta["coordinate_system"] = str(src.crs)[:95]
        return meta
    except ImportError:
        logging.warning("Neither GDAL nor rasterio available for metadata extraction")
    except Exception as e:
        logging.warning("rasterio metadata extraction failed: %s", e)

    return meta


def _bg_generate_description(meta, layer_name, data_type, record_id, model_class, app):
    """Background: call the configured (OpenAI-compatible) AI API to auto-generate a data description."""
    try:
        api_base, api_key, model = _get_ai_config()
        if not api_key:
            return

        import httpx

        if data_type == "raster":
            prompt = f"""你是一个地理空间数据专家。请根据以下元数据，用中文写一段简洁的数据简介（100-200字），说明数据内容、覆盖范围、分辨率、波段信息等。

文件名：{layer_name}
波段数：{meta.get("bands", "未知")}
像素类型：{meta.get("pixel_type", "未知")}
分辨率：{meta.get("resolution", "未知")}
坐标系：{meta.get("coordinate_system", "未知")}
文件大小：{meta.get("file_size", 0) / 1024 / 1024:.1f} MB

请直接输出简介文本，不要加标题或前缀。"""
        else:
            prompt = f"""你是一个地理空间数据专家。请根据以下元数据，用中文写一段简洁的数据简介（100-200字），说明数据内容、几何类型、坐标系等。

文件名：{layer_name}
几何类型：{meta.get("geomtype", "未知")}
坐标系：{meta.get("coordinate_system", "未知")}

请直接输出简介文本，不要加标题或前缀。"""

        resp = httpx.post(
            _chat_completions_url(api_base),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300,
                "temperature": 0.7,
            },
            timeout=_get_ai_timeout(),
        )
        if resp.status_code == 200:
            reply = resp.json()["choices"][0]["message"]["content"].strip()
            with app.app_context():
                record = model_class.query.get(record_id)
                if record and (not record.introduction or record.introduction == "暂无简介"):
                    record.introduction = reply
                    db.session.commit()
                    logging.info("AI description generated for %s id=%s", data_type, record_id)
    except Exception as e:
        logging.warning("AI description generation failed: %s", e)


def _safe_extract_zip(zip_ref, dest_dir):
    for member in zip_ref.namelist():
        target = os.path.realpath(os.path.join(dest_dir, member))
        if not target.startswith(os.path.realpath(dest_dir)):
            raise ValueError(f"非法文件路径: {member}")
    zip_ref.extractall(dest_dir)


def _cleanup_upload_artifacts(save_path, extract_dir):
    """Best-effort removal of the saved zip and extracted directory of a failed upload."""
    try:
        if save_path and os.path.exists(save_path):
            os.remove(save_path)
        if extract_dir and os.path.isdir(extract_dir):
            shutil.rmtree(extract_dir, ignore_errors=True)
    except Exception:
        logging.warning("上传失败后清理残留文件时出错 (save_path=%s, extract_dir=%s)", save_path, extract_dir)


class ShpDataUploadResource(Resource):
    @admin_required
    @limiter.limit("10 per minute")
    def post(self):
        data_alias = (request.form.get("data_alias") or "").strip()
        category = (request.form.get("category") or "").strip()
        data_introduction = (request.form.get("data_introduction") or "").strip()

        if not data_alias:
            return {"status": False, "msg": "数据名称不能为空"}, 400

        if "file" not in request.files:
            return {"status": False, "msg": "未找到上传文件"}, 400

        file = request.files["file"]
        if not file.filename or not file.filename.lower().endswith(".zip"):
            return {"status": False, "msg": "仅支持 .zip 格式文件"}, 400

        save_path = None
        extract_dir = None
        try:
            filename = secure_filename(file.filename)
            upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "shp_uploads")
            os.makedirs(upload_dir, exist_ok=True)

            save_path = os.path.join(upload_dir, filename)
            file.save(save_path)

            extract_dir = os.path.join(upload_dir, os.path.splitext(filename)[0])
            os.makedirs(extract_dir, exist_ok=True)

            with zipfile.ZipFile(save_path, "r") as zf:
                _safe_extract_zip(zf, extract_dir)

            shp_files = []
            for root, _, files in os.walk(extract_dir):
                for f in files:
                    if f.lower().endswith(".shp"):
                        shp_files.append(os.path.join(root, f))

            if len(shp_files) != 1:
                _cleanup_upload_artifacts(save_path, extract_dir)
                return {
                    "status": False,
                    "msg": f"ZIP包中应包含且仅包含一个 .shp 文件，当前找到 {len(shp_files)} 个",
                }, 400

            shp_file_path = shp_files[0]
            geomtype = "Unknown"
            coordinate_system = None
            layer_name = os.path.splitext(os.path.basename(shp_file_path))[0]

            try:
                import fiona

                with fiona.open(shp_file_path) as src:
                    if src.schema and src.schema.get("geometry"):
                        geomtype = src.schema["geometry"]
                    if src.crs:
                        from pyproj import CRS

                        try:
                            epsg = CRS.from_user_input(src.crs).to_epsg()
                            coordinate_system = f"EPSG:{epsg}" if epsg else str(src.crs)[:95]
                        except Exception:
                            coordinate_system = str(src.crs)[:95]
            except Exception:
                logging.warning(f"无法读取SHP元数据: {shp_file_path}")

            record = Shp(
                name=layer_name,
                alias=data_alias,
                geomtype=geomtype,
                introduction=data_introduction or "暂无简介",
                datetime=datetime.now(UTC),
                url="",
                layer=layer_name,
                shp_file_path=shp_file_path,
                coordinate_system=coordinate_system,
                data_source=category or "未分类",
            )
            db.session.add(record)
            db.session.commit()

            app_obj = current_app._get_current_object()

            # Auto-publish to GeoServer in background thread
            try:
                t = threading.Thread(
                    target=_bg_publish_geoserver,
                    args=(save_path, layer_name, "shp", record.id, Shp, app_obj),
                    daemon=True,
                )
                t.start()
            except Exception:
                logging.warning("Failed to start background GeoServer publish for SHP")

            # Auto-generate AI description if user didn't provide one
            if not data_introduction:
                shp_meta = {"geomtype": geomtype, "coordinate_system": coordinate_system}
                try:
                    t = threading.Thread(
                        target=_bg_generate_description,
                        args=(shp_meta, layer_name, "shp", record.id, Shp, app_obj),
                        daemon=True,
                    )
                    t.start()
                except Exception:
                    logging.warning("Failed to start AI description generation for SHP")

            return {"status": True, "msg": "数据上传成功", "data": record.to_dict()}, 201

        except ValueError as e:
            _cleanup_upload_artifacts(save_path, extract_dir)
            return {"status": False, "msg": str(e)}, 400
        except Exception as e:
            db.session.rollback()
            logging.error(str(e))
            _cleanup_upload_artifacts(save_path, extract_dir)
            return {"status": False, "msg": "上传失败，请稍后重试"}, 500


class RasterDataUploadResource(Resource):
    @admin_required
    @limiter.limit("10 per minute")
    def post(self):
        data_alias = (request.form.get("data_alias") or "").strip()
        category = (request.form.get("category") or "").strip()
        data_introduction = (request.form.get("data_introduction") or "").strip()

        if not data_alias:
            return {"status": False, "msg": "数据名称不能为空"}, 400

        if "file" not in request.files:
            return {"status": False, "msg": "未找到上传文件"}, 400

        file = request.files["file"]
        allowed_ext = (".tif", ".tiff", ".img", ".png", ".jpg", ".jpeg")
        if not file.filename or not any(file.filename.lower().endswith(e) for e in allowed_ext):
            return {"status": False, "msg": "仅支持 TIFF/PNG/JPG 格式的栅格文件"}, 400

        try:
            filename = secure_filename(file.filename)
            upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "raster_uploads")
            os.makedirs(upload_dir, exist_ok=True)

            save_path = os.path.join(upload_dir, filename)
            file.save(save_path)

            # Extract raster metadata (bands, pixel_type, resolution, CRS)
            raster_meta = _extract_raster_metadata(save_path)

            record = RasterData(
                name=os.path.splitext(filename)[0],
                alias=data_alias,
                introduction=data_introduction or "暂无简介",
                datetime=datetime.now(UTC),
                url="",
                layer="",
                raster_file_path=save_path,
                coordinate_system=raster_meta.get("coordinate_system"),
                data_source=category or "未分类",
                band_count=raster_meta.get("bands", 0),
                pixel_type=raster_meta.get("pixel_type"),
            )
            db.session.add(record)
            db.session.commit()

            app_obj = current_app._get_current_object()

            # (tiles are rendered on demand from the source file — no pre-generation)

            # Auto-publish to GeoServer in background thread
            raster_layer_name = os.path.splitext(filename)[0]
            try:
                t = threading.Thread(
                    target=_bg_publish_geoserver,
                    args=(save_path, raster_layer_name, "raster", record.id, RasterData, app_obj),
                    daemon=True,
                )
                t.start()
            except Exception:
                logging.warning("Failed to start background GeoServer publish for raster")

            # Auto-generate AI description if user didn't provide one
            if not data_introduction:
                try:
                    t = threading.Thread(
                        target=_bg_generate_description,
                        args=(raster_meta, raster_layer_name, "raster", record.id, RasterData, app_obj),
                        daemon=True,
                    )
                    t.start()
                except Exception:
                    logging.warning("Failed to start AI description generation for raster")

            return {"status": True, "msg": "栅格数据上传成功", "data": record.to_dict()}, 201

        except Exception as e:
            db.session.rollback()
            logging.error(str(e))
            return {"status": False, "msg": "上传失败，请稍后重试"}, 500


class GeoServerPublishResource(Resource):
    """手动触发将已上传的数据发布到 GeoServer（用于 GeoServer 未运行时上传的数据）"""

    @admin_required
    def post(self):
        data = request.get_json() or {}
        data_type = data.get("data_type")  # "vector" or "raster"
        data_id = data.get("data_id")

        if not data_type or not data_id:
            return {"status": False, "msg": "需要 data_type 和 data_id"}, 400

        try:
            if data_type == "vector":
                record = Shp.query.get(data_id)
                if not record:
                    return {"status": False, "msg": f"矢量数据 #{data_id} 不存在"}, 404
                file_path = record.shp_file_path
                layer_name = record.name
                # For SHP, we need the zip file
                zip_dir = os.path.dirname(file_path)
                zip_path = None
                for f in os.listdir(zip_dir):
                    if f.lower().endswith(".zip"):
                        zip_path = os.path.join(zip_dir, f)
                        break
                if not zip_path:
                    # Create a zip from the shp directory
                    zip_path = os.path.join(zip_dir, f"{layer_name}.shp.zip")
                    shp_dir = os.path.dirname(file_path)
                    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                        for root, _, files in os.walk(shp_dir):
                            for fn in files:
                                full = os.path.join(root, fn)
                                arcname = os.path.relpath(full, shp_dir)
                                zf.write(full, arcname)

                from utils.geoserver_utils import publish_shapefile

                result = publish_shapefile(zip_path, layer_name)

            elif data_type == "raster":
                record = RasterData.query.get(data_id)
                if not record:
                    return {"status": False, "msg": f"栅格数据 #{data_id} 不存在"}, 404
                file_path = record.raster_file_path
                layer_name = record.name

                from utils.geoserver_utils import publish_geotiff

                result = publish_geotiff(file_path, layer_name)
            else:
                return {"status": False, "msg": "data_type 必须是 vector 或 raster"}, 400

            if result["success"]:
                record.url = result["wms_url"]
                record.layer = result["layer"]
                db.session.commit()
                return {
                    "status": True,
                    "msg": "发布成功",
                    "data": {"wms_url": result["wms_url"], "layer": result["layer"]},
                }, 200
            else:
                return {"status": False, "msg": f"GeoServer 发布失败: {result.get('error')}"}, 502

        except Exception as e:
            db.session.rollback()
            logging.error("GeoServer publish error: %s", e, exc_info=True)
            return {"status": False, "msg": f"发布失败: {str(e)[:200]}"}, 500


class GeoServerStatusResource(Resource):
    """检查 GeoServer 连接状态"""

    @jwt_required()
    def get(self):
        import httpx

        from utils.geoserver_utils import _auth, _base

        try:
            r = httpx.get(f"{_base()}/rest/about/version", auth=_auth(), timeout=5)
            if r.status_code == 200:
                return {"status": True, "msg": "GeoServer 连接正常", "data": {"url": _base()}}, 200
            return {"status": False, "msg": f"GeoServer 返回 {r.status_code}"}, 502
        except Exception as e:
            return {"status": False, "msg": f"GeoServer 不可用: {str(e)[:100]}"}, 503


class DataEditResource(Resource):
    """编辑数据记录的元信息（简介、分类、别名）"""

    @admin_required
    def put(self, data_type, data_id):
        """Update metadata for a vector or raster record."""
        data = request.get_json() or {}
        if not data:
            return {"status": False, "msg": "请求体不能为空"}, 400

        try:
            if data_type == "vector":
                record = Shp.query.get(data_id)
            elif data_type == "raster":
                record = RasterData.query.get(data_id)
            else:
                return {"status": False, "msg": "data_type 必须是 vector 或 raster"}, 400

            if not record:
                return {"status": False, "msg": f"数据 #{data_id} 不存在"}, 404

            # Update allowed fields
            if "alias" in data:
                record.alias = data["alias"]
            if "introduction" in data:
                record.introduction = data["introduction"]
            if "data_source" in data:
                record.data_source = data["data_source"]

            db.session.commit()
            return {"status": True, "msg": "更新成功", "data": record.to_dict()}, 200

        except Exception as e:
            db.session.rollback()
            logging.error("Data edit error: %s", e, exc_info=True)
            return {"status": False, "msg": f"更新失败: {str(e)[:200]}"}, 500

    @jwt_required()
    def get(self, data_type, data_id):
        """Get single record detail."""
        try:
            if data_type == "vector":
                record = Shp.query.get(data_id)
            elif data_type == "raster":
                record = RasterData.query.get(data_id)
            else:
                return {"status": False, "msg": "data_type 必须是 vector 或 raster"}, 400

            if not record:
                return {"status": False, "msg": f"数据 #{data_id} 不存在"}, 404

            return {"status": True, "data": record.to_dict()}, 200
        except Exception as e:
            logging.error("Data detail error: %s", e)
            return {"status": False, "msg": "查询失败"}, 500


class DataListResource(Resource):
    """获取数据列表（支持分页、筛选）"""

    @jwt_required()
    def get(self, data_type):
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("pageSize", 20, type=int)
        keyword = request.args.get("keyword", "").strip()

        try:
            if data_type == "vector":
                query = Shp.query
            elif data_type == "raster":
                query = RasterData.query
            else:
                return {"status": False, "msg": "data_type 必须是 vector 或 raster"}, 400

            if keyword:
                query = query.filter(
                    db.or_(
                        Shp.name.contains(keyword) if data_type == "vector" else RasterData.name.contains(keyword),
                        Shp.alias.contains(keyword) if data_type == "vector" else RasterData.alias.contains(keyword),
                    )
                )

            total = query.count()
            records = (
                query.order_by(Shp.id.desc() if data_type == "vector" else RasterData.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )

            return {
                "status": True,
                "data": {
                    "list": [r.to_dict() for r in records],
                    "total": total,
                    "page": page,
                    "pageSize": page_size,
                },
            }, 200
        except Exception as e:
            logging.error("Data list error: %s", e)
            return {"status": False, "msg": "查询失败"}, 500


class DataDeleteResource(Resource):
    """删除数据记录"""

    @admin_required
    def delete(self, data_type, data_id):
        try:
            if data_type == "vector":
                record = Shp.query.get(data_id)
            elif data_type == "raster":
                record = RasterData.query.get(data_id)
            else:
                return {"status": False, "msg": "data_type 必须是 vector 或 raster"}, 400

            if not record:
                return {"status": False, "msg": f"数据 #{data_id} 不存在"}, 404

            layer_name = record.name

            # Delete from GeoServer if published
            try:
                from utils.geoserver_utils import delete_layer

                delete_layer(layer_name)
            except Exception:
                pass

            db.session.delete(record)
            db.session.commit()
            return {"status": True, "msg": f"数据 #{data_id} 已删除"}, 200

        except Exception as e:
            db.session.rollback()
            logging.error("Data delete error: %s", e)
            return {"status": False, "msg": f"删除失败: {str(e)[:200]}"}, 500
