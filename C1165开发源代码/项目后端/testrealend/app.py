# import os
# from flask import Flask, send_from_directory, jsonify, request # 确保导入 request
# from flask_jwt_extended import JWTManager
# from datetime import timedelta
# from flask_migrate import Migrate
# from extension.extension import db # 假设 limiter 已经从这里移除了，或者你不需要它了
# from flask_restful import Api, Resource
# from flask_cors import CORS

# # 导入你已有的资源
# from resource.common_resource import RegisterResource,LogoutResource, LoginResource, ProtectResource, RefreshTokenResource
# from resource.nav_resource import AdmNavResource1, EmpNavResource1
# from resource.adm_resource import GetEmpInfoList, WatermarkEmbeddingResource, \
#     GetEmpPhotoResource, Adm1GetApplicationsGenerateWatermark, Adm2EmbeddingWatermark
#     # 假设你还有其他 adm_resource 导入，保持它们
# from resource.shp_data_resource import ShpDataListResource, ShpDataByIdResource
# from resource.application_resource import (SubmitApplicationResource, Adm1GetApplicationsResource,
#                                            Adm2GetApplicationsResource, Adm2FailResource, Adm2PassResource,
#                                            Adm1FailResource, Adm1PassResource, Adm1GetApproved, Adm2GetApproved,
#                                            EmpGetApplications)
# from resource.generate_watermark import GenerateQrcodeResource
# from resource.embed_watermark import GetAppQRcode
# from resource.emp_resource import EmpGetApprovedApplications, EmpDownloadZip
# from resource.download_file_resource import RecordDownload
# from resource.receive_zip_to_extract import UploadFile
# from resource.log_resource import SystemLogResource


# app = Flask(__name__)
# app.config['SECRET_KEY'] = 'your-secret-key'

# # 【推荐】将所有反斜杠 \ 改为正斜杠 /
# app.config['UPLOAD_FOLDER'] = 'D:/Desktop/MyProjects/Spatial_Data_Tracking_System_lastvension/test/upload_folder'
# app.config['WATERMARK_FOLDER'] = 'D:/Desktop/MyProjects/Spatial_Data_Tracking_System_lastvension/test/watermark_folder' 
# app.config['STATIC_URL_PATH'] = '/uploads' # 服务的URL前缀
# app.config['STATIC_FOLDER'] = app.config['WATERMARK_FOLDER'] # 指向水印文件夹

# app.config['SQLALCHEMY_BINDS'] = {
#     'mysql_db': 'mysql+mysqldb://root:root@127.0.0.1/esri_test',
#     'postgres_db': 'postgresql://postgres:root@127.0.0.1/esri_test'
# }
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# app.config['JWT_SECRET_KEY'] = 'your-jwt-secret-key'
# app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
# app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

# db.init_app(app)
# migrate = Migrate(app, db)
# # limiter.init_app(app) # 如果你暂时不用limiter，可以注释掉

# # ==================== CORS 配置 ====================
# # 对于开发，允许特定前端源；生产环境应更严格
# CORS(app,
#      origins=["http://localhost:5174", "http://localhost:5173"], # 允许你的Vue前端端口 (你之前提到过5173和5174)
#      methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
#      allow_headers=["Content-Type", "Authorization", "X-Requested-With"], # 根据前端实际发送的头部调整
#      expose_headers=["Content-Disposition"], # 如果前端需要读取这个响应头
#      supports_credentials=True
# )
# # ======================================================

# jwt = JWTManager(app)
# api = Api(app)

# # --- 公共资源 ---
# api.add_resource(RegisterResource, '/api/register')
# api.add_resource(LoginResource, '/api/login')
# api.add_resource(LogoutResource, '/api/logout')
# api.add_resource(ProtectResource, '/api/protected')
# api.add_resource(RefreshTokenResource, '/api/refresh-token')

# # --- 管理员资源 ---
# api.add_resource(AdmNavResource1, '/api/admin/nav/tree')
# api.add_resource(GetEmpInfoList, '/api/adm/get_emp_info_list')
# api.add_resource(WatermarkEmbeddingResource, '/api/admin/watermark_embedding')
# api.add_resource(GetEmpPhotoResource, '/api/employee/photo/<string:employee_number>')
# api.add_resource(Adm1GetApplicationsResource, '/api/adm1_get_applications')
# api.add_resource(Adm2GetApplicationsResource, '/api/adm2_get_applications')
# api.add_resource(Adm1GetApproved, '/api/adm1_get_approved')
# api.add_resource(Adm2GetApproved, '/api/adm2_get_approved')
# api.add_resource(Adm1PassResource, '/api/adm1_pass')
# api.add_resource(Adm1FailResource, '/api/adm1_fail')
# api.add_resource(Adm2PassResource, '/api/adm2_pass')
# api.add_resource(Adm2FailResource, '/api/adm2_fail')
# api.add_resource(Adm1GetApplicationsGenerateWatermark, '/api/adm1_get_applications_generate_watermark', endpoint='generate_watermark_adm1') # 确保endpoint唯一
# api.add_resource(GenerateQrcodeResource, '/api/generate_watermark') # 确保这个endpoint也唯一，或者与上面的不同
# api.add_resource(Adm2EmbeddingWatermark, '/api/adm2_embedding_watermark_applications', endpoint='embedding_watermark_adm2') # 确保endpoint唯一
# api.add_resource(GetAppQRcode, '/api/embedding_watermark') # 确保这个endpoint也唯一

# # --- 员工资源 ---
# api.add_resource(EmpNavResource1, '/api/employee/nav/tree')
# # 【重要】修改了ShpDataListResource的端点和之前的冲突
# api.add_resource(ShpDataListResource, '/api/data_viewing', endpoint='shp_data_list') # 用于获取列表
# # api.add_resource(ShpDataListResource, '/api/data_viewing/pageList', endpoint='shp_data_list_legacy') # 如果还想保留旧的，给个新endpoint
# # api.add_resource(ShpDataListResource, '/api/data_viewing/search', endpoint='search_data') # 如果search也是用ShpDataListResource，确保endpoint唯一
# api.add_resource(ShpDataByIdResource, '/api/data_viewing/getById', endpoint='shp_data_by_id')
# api.add_resource(SubmitApplicationResource, '/api/submit_application')
# api.add_resource(EmpGetApplications, '/api/get_applications')
# api.add_resource(EmpGetApprovedApplications, '/api/get_approved_applications')
# api.add_resource(EmpDownloadZip, '/api/emp_download_zip')
# api.add_resource(RecordDownload, '/api/record_download_file')

# # --- 文件上传 ---
# api.add_resource(UploadFile, '/api/upload_zip')
# # api.add_resource(ShpUploadResource, '/api/shp/upload') # 如果你有ShpUploadResource，取消注释并确保导入

# # ==================== 新增：注册日志API资源 ====================
# api.add_resource(SystemLogResource, '/api/admin/logs') # 新的API端点
# # ===============================================================


# @app.route('/uploads/<path:filename>')
# def serve_watermark(filename):
#     # 【修改】使用 app.config['WATERMARK_FOLDER'] 作为静态文件夹的根目录
#     # 并且 send_from_directory 的第一个参数应该是目录，第二个是相对于该目录的文件名
#     # 你的 STATIC_FOLDER 已经指向 WATERMARK_FOLDER
#     # 所以这里应该是正确的，只要 WATERMARK_FOLDER 配置正确
#     static_folder_root = app.config['STATIC_FOLDER']
    
#     # 如果 STATIC_FOLDER 是 'E:/水印提取/watermark/'
#     # 而 filename 是 'some_image.png'
#     # 那么 file_path 会是 'E:/水印提取/watermark/some_image.png'
#     file_path = os.path.join(static_folder_root, filename)

#     if os.path.exists(file_path):
#         return send_from_directory(static_folder_root, filename)
#     else:
#         return jsonify({"error": f"File {filename} not found in {static_folder_root}"}), 404


# if __name__ == '__main__':
#     # 确保上传文件夹存在
#     upload_dir = os.path.abspath(app.config['UPLOAD_FOLDER']) # 获取绝对路径
#     if not os.path.exists(upload_dir):
#         try:
#             os.makedirs(upload_dir)
#             print(f"Created upload directory: {upload_dir}")
#         except Exception as e:
#             print(f"Error creating upload directory {upload_dir}: {e}")

#     # 确保水印文件夹（作为静态文件夹）存在，如果 serve_watermark 要用的话
#     watermark_dir = os.path.abspath(app.config['WATERMARK_FOLDER'])
#     if not os.path.exists(watermark_dir):
#         try:
#             os.makedirs(watermark_dir)
#             print(f"Created watermark directory: {watermark_dir}")
#         except Exception as e:
#             print(f"Error creating watermark directory {watermark_dir}: {e}")
            
#     app.run(debug=True, port=5001)


import os
import sys
import traceback
from flask import Flask, send_from_directory, jsonify, request, send_file
from flask_jwt_extended import JWTManager
from datetime import timedelta
from flask_migrate import Migrate
from extension.extension import db
from flask_restful import Api, Resource
from flask_cors import CORS

# 获取当前文件路径和项目根目录
current_file_path = os.path.abspath(__file__)
script_dir = os.path.dirname(current_file_path)
project_root = os.path.dirname(script_dir)  # 获取项目根目录

# 添加项目根目录到系统路径
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 添加模型目录到系统路径
model_dir = os.path.join(project_root, 'model')
if model_dir not in sys.path:
    sys.path.insert(0, model_dir)

# 导入你已有的资源
from resource.common_resource import RegisterResource, LogoutResource, LoginResource, ProtectResource, RefreshTokenResource
from resource.nav_resource import AdmNavResource1, EmpNavResource1
from resource.adm_resource import GetEmpInfoList, WatermarkEmbeddingResource, \
    GetEmpPhotoResource, Adm1GetApplicationsGenerateWatermark, Adm2EmbeddingWatermark
from resource.shp_data_resource import ShpDataListResource, ShpDataByIdResource
from resource.application_resource import (SubmitApplicationResource, Adm1GetApplicationsResource,
                                          Adm2GetApplicationsResource, Adm2FailResource, Adm2PassResource,
                                          Adm1FailResource, Adm1PassResource, Adm1GetApproved, Adm2GetApproved,
                                          EmpGetApplications)
from resource.generate_watermark import GenerateQrcodeResource
from resource.embed_watermark import GetAppQRcode
from resource.emp_resource import EmpGetApprovedApplications, EmpDownloadZip
from resource.download_file_resource import RecordDownload
from resource.receive_zip_to_extract import UploadFile
from resource.log_resource import SystemLogResource

# 导入栅格水印API资源
from resource.raster_watermark_resource import RasterEmbedResource, RasterExtractResource

# 导入栅格数据资源
from resource.raster_data_resource import RasterDataListResource, RasterDataByIdResource

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'

# 文件夹配置
app.config['UPLOAD_FOLDER'] = 'D:/Desktop/MyProjects/Spatial_Data_Tracking_System_lastvension/test/upload_folder'
app.config['EMBED_FOLDER'] = 'D:/Desktop/MyProjects/Spatial_Data_Tracking_System_lastvension/testrealend/embed'
app.config['EXTRACTED_FOLDER'] = 'D:/Desktop/MyProjects/Spatial_Data_Tracking_System_lastvension/testrealend/extracted'
app.config['WATERMARK_FOLDER'] = 'D:/Desktop/MyProjects/Spatial_Data_Tracking_System_lastvension/test/watermark_folder' 
app.config['STATIC_URL_PATH'] = '/uploads'
app.config['STATIC_FOLDER'] = app.config['WATERMARK_FOLDER']

# 数据库配置
app.config['SQLALCHEMY_BINDS'] = {
    'mysql_db': 'mysql+mysqldb://root:root@127.0.0.1/esri_test',
    'postgres_db': 'postgresql://postgres:root@127.0.0.1/esri_test'
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'your-jwt-secret-key'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

# 初始化扩展
db.init_app(app)
migrate = Migrate(app, db)

# CORS配置
CORS(app,
     origins=["http://localhost:5174", "http://localhost:5173"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
     expose_headers=["Content-Disposition"],
     supports_credentials=True
)

jwt = JWTManager(app)
api = Api(app)

# 注册所有API资源
# 公共资源
api.add_resource(RegisterResource, '/api/register')
api.add_resource(LoginResource, '/api/login')
api.add_resource(LogoutResource, '/api/logout')
api.add_resource(ProtectResource, '/api/protected')
api.add_resource(RefreshTokenResource, '/api/refresh-token')

# 管理员资源
api.add_resource(AdmNavResource1, '/api/admin/nav/tree')
api.add_resource(GetEmpInfoList, '/api/adm/get_emp_info_list')
api.add_resource(WatermarkEmbeddingResource, '/api/admin/watermark_embedding')
api.add_resource(GetEmpPhotoResource, '/api/employee/photo/<string:employee_number>')
api.add_resource(Adm1GetApplicationsResource, '/api/adm1_get_applications')
api.add_resource(Adm2GetApplicationsResource, '/api/adm2_get_applications')
api.add_resource(Adm1GetApproved, '/api/adm1_get_approved')
api.add_resource(Adm2GetApproved, '/api/adm2_get_approved')
api.add_resource(Adm1PassResource, '/api/adm1_pass')
api.add_resource(Adm1FailResource, '/api/adm1_fail')
api.add_resource(Adm2PassResource, '/api/adm2_pass')
api.add_resource(Adm2FailResource, '/api/adm2_fail')
api.add_resource(Adm1GetApplicationsGenerateWatermark, '/api/adm1_get_applications_generate_watermark', endpoint='generate_watermark_adm1')
api.add_resource(GenerateQrcodeResource, '/api/generate_watermark')
api.add_resource(Adm2EmbeddingWatermark, '/api/adm2_embedding_watermark_applications', endpoint='embedding_watermark_adm2')
api.add_resource(GetAppQRcode, '/api/embedding_watermark')

# 员工资源
api.add_resource(EmpNavResource1, '/api/employee/nav/tree')
api.add_resource(ShpDataListResource, '/api/vector_data_viewing', endpoint='vector_data_list')
api.add_resource(ShpDataByIdResource, '/api/vector_data_viewing/getById', endpoint='vector_data_by_id')
api.add_resource(SubmitApplicationResource, '/api/submit_application')
api.add_resource(EmpGetApplications, '/api/get_applications')
api.add_resource(EmpGetApprovedApplications, '/api/get_approved_applications')
api.add_resource(EmpDownloadZip, '/api/emp_download_zip')
api.add_resource(RecordDownload, '/api/record_download_file')

# 栅格数据资源
api.add_resource(RasterDataListResource, '/api/raster_data_viewing', endpoint='raster_data_list')
api.add_resource(RasterDataByIdResource, '/api/raster_data_viewing/getById', endpoint='raster_data_by_id')

# 文件上传
api.add_resource(UploadFile, '/api/upload_zip')

# 日志
api.add_resource(SystemLogResource, '/api/admin/logs')

# 栅格水印资源
api.add_resource(RasterEmbedResource, '/api/raster/embed')
api.add_resource(RasterExtractResource, '/api/raster/extract')

# 统一数据接口
class UnifiedDataListResource(Resource):
    def get(self):
        try:
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('pageSize', 10))
            keyword = request.args.get('keyword', '')
            data_type = request.args.get('dataType', 'all')  # all, vector, raster
            
            # 获取矢量数据
            vector_list = []
            vector_pagination = {}
            if data_type in ['all', 'vector']:
                from server.shp_data_server import ShpDataServer
                shp_server = ShpDataServer()
                vector_list, vector_pagination = shp_server.get_data_list(page, page_size, keyword)
            
            # 获取栅格数据
            raster_list = []
            raster_pagination = {}
            if data_type in ['all', 'raster']:
                from server.raster_data_server import RasterDataServer
                raster_server = RasterDataServer()
                raster_list, raster_pagination = raster_server.get_data_list(page, page_size, keyword)
            
            # 合并结果
            combined_list = vector_list + raster_list
            total_count = vector_pagination.get('total', 0) + raster_pagination.get('total', 0)
            
            return {
                'code': 200,
                'msg': 'success',
                'data': {
                    'list': combined_list,
                    'pages': {
                        'page': page,
                        'pageSize': page_size,
                        'total': total_count,
                        'pages': (total_count + page_size - 1) // page_size
                    }
                }
            }
        except Exception as e:
            traceback.print_exc()
            return {'msg': str(e), 'status': False}, 500

# 注册统一数据接口
api.add_resource(UnifiedDataListResource, '/api/data_viewing')

@app.route('/uploads/<path:filename>')
def serve_watermark(filename):
    static_folder_root = app.config['STATIC_FOLDER']
    file_path = os.path.join(static_folder_root, filename)
    if os.path.exists(file_path):
        return send_from_directory(static_folder_root, filename)
    else:
        return jsonify({"error": f"File {filename} not found in {static_folder_root}"}), 404

# 栅格数据下载接口
@app.route('/api/raster_data/download/<int:data_id>')
def download_raster_data(data_id):
    from model.Raster_Data import RasterData  # 使用正确的模型路径
    raster_data = RasterData.query.get(data_id)
    if not raster_data:
        return jsonify({"error": "文件不存在"}), 404
    file_path = raster_data.file_path
    if not os.path.exists(file_path):
        return jsonify({"error": "文件不存在"}), 404
    return send_file(file_path, as_attachment=True, download_name=os.path.basename(file_path))

if __name__ == '__main__':
    # 自动创建所有需要的文件夹
    for folder_key in ['UPLOAD_FOLDER', 'EMBED_FOLDER', 'EXTRACTED_FOLDER', 'WATERMARK_FOLDER']:
        folder_path = app.config.get(folder_key)
        if folder_path and not os.path.exists(folder_path):
            try:
                os.makedirs(folder_path)
                print(f"Created directory: {folder_path}")
            except Exception as e:
                print(f"Error creating directory {folder_path}: {e}")
    
    # 额外创建 raster 和 temp 子文件夹
    for base_folder in ['EMBED_FOLDER', 'EXTRACTED_FOLDER', 'UPLOAD_FOLDER']:
        raster_dir = os.path.join(app.config[base_folder], 'raster')
        temp_dir = os.path.join(app.config[base_folder], 'temp')
        os.makedirs(raster_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)
            
    app.run(debug=True, port=5001)