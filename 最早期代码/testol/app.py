import os
from flask import Flask, send_from_directory, jsonify
from flask_jwt_extended import JWTManager
from datetime import timedelta
from flask_migrate import Migrate
from extension.extension import db, limiter
from flask_restful import Api, Resource
from flask_cors import CORS

# 导入资源
from resource.common_resource import LogoutResource, LoginResource, ProtectResource, RefreshTokenResource

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

from resource.receive_zip_to_extract import UploadFile, GetOriginalWatermark, UploadWatermarks

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'

# app.config['JSON_AS_ASCII'] = False

# # 配置上传文件夹
# app.config['UPLOAD_FOLDER'] = r'E:\数据上传'

app.config['UPLOAD_FOLDER'] = 'E:/数据上传/'
app.config['WATERMARK_FOLDER'] = 'E:/水印提取/watermark/'
app.config['STATIC_URL_PATH'] = '/uploads'
app.config['STATIC_FOLDER'] = app.config['WATERMARK_FOLDER']


# # 云服务器数据库配置
# app.config['SQLALCHEMY_BINDS'] = {
#     'mysql_db': 'mysql+mysqldb://root:123456@127.0.0.1/testreal',
#     'postgres_db': 'postgresql://postgres:KANGsumeng2003-@127.0.0.1/test'
# }


# 配置数据库绑定
app.config['SQLALCHEMY_BINDS'] = {
    'mysql_db': "mysql+pymysql://root:root@127.0.0.1/esri_test",
    'postgres_db': 'postgresql://postgres:root@127.0.0.1/ESRI_test'
}

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# JWT 配置
app.config['JWT_SECRET_KEY'] = 'your-jwt-secret-key'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

db.init_app(app)

migrate = Migrate(app, db)

# limiter.init_app(app)

# CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": "http://localhost:5173"}})

CORS(app, resources={r"/*": {"origins": "*"}})

# CORS(app, resources={r"/uploads/*": {"origins": "*"}})

CORS(app, expose_headers=['Content-Disposition'])

jwt = JWTManager(app)

api = Api(app)

# 公共资源
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

api.add_resource(Adm1GetApplicationsGenerateWatermark, '/api/adm1_get_applications_generate_watermark',
                 endpoint='generate_watermark')
api.add_resource(GenerateQrcodeResource, '/api/generate_watermark')
api.add_resource(Adm2EmbeddingWatermark, '/api/adm2_embedding_watermark_applications', endpoint='embedding_watermark')

# 数据嵌入二维码
api.add_resource(GetAppQRcode, '/api/embedding_watermark')

# 员工资源
api.add_resource(EmpNavResource1, '/api/employee/nav/tree')
api.add_resource(ShpDataListResource, '/api/data_viewing/pageList', endpoint='shp_data_list')
api.add_resource(ShpDataByIdResource, '/api/data_viewing/getById', endpoint='shp_data_by_id')
api.add_resource(ShpDataListResource, '/api/data_viewing/search', endpoint='search_data')
api.add_resource(SubmitApplicationResource, '/api/submit_application')
api.add_resource(EmpGetApplications, '/api/get_applications')
api.add_resource(EmpGetApprovedApplications, '/api/get_approved_applications')
api.add_resource(EmpDownloadZip, '/api/emp_download_zip')
api.add_resource(RecordDownload, '/api/record_download_file')

# 文件上传
api.add_resource(UploadFile, '/api/upload_zip')
api.add_resource(GetOriginalWatermark, '/api/get_original_watermark')
api.add_resource(UploadWatermarks, '/api/upload/ori&ext_watermark')


@app.route('/uploads/<path:filename>')
def serve_watermark(filename):
    file_path = os.path.join(app.config['STATIC_FOLDER'], filename)
    # 检查文件是否存在
    if os.path.exists(file_path):
        return send_from_directory(app.config['STATIC_FOLDER'], filename)
    else:
        # 返回一个更标准的 JSON 错误响应
        return {"error": f"File {filename} not found"}, 404


if __name__ == '__main__':
    app.run(debug=True)

