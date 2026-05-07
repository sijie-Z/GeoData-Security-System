import os
import platform

# Work around Windows WMI hangs triggered by platform.machine() during
# SQLAlchemy/Alembic import on some environments.
if os.name == "nt":
    try:
        platform.machine = lambda: os.environ.get("PROCESSOR_ARCHITECTURE", "AMD64")
    except Exception:
        pass

from flask import Flask, send_from_directory, jsonify, request
from flask_jwt_extended import JWTManager
from datetime import timedelta
from flask_migrate import Migrate
from flask_restful import Api
from flask_cors import CORS
from extension.extension import db, limiter
from dotenv import load_dotenv
try:
    from flasgger import Swagger
    _has_flasgger = True
except ImportError:
    _has_flasgger = False

load_dotenv()


def _bootstrap_runtime_schema(app):
    """
    Ensure core tables exist so first-time deployments don't fail with 500 due
    to missing tables.
    """
    from model.Adm_Account import AdmAccount
    from model.Adm_Info import AdmInfo
    from model.Adm_Nav import AdmNav
    from model.Announcement import Announcement
    from model.Application import Application
    from model.ChatMessage import ChatMessage
    from model.Download_Record import DownloadRecord
    from model.EmployeeNotification import EmployeeNotification
    from model.Employee_Account import EmployeeAccount
    from model.Employee_Info import EmployeeInfo
    from model.Employee_Nav import EmployeeNav
    from model.FriendRequest import FriendRequest
    from model.Log_Info import LogInfo
    from model.Raster_Data import RasterData
    from model.Shp_Data import Shp
    from model.RecallProposal import RecallProposal
    from model.AdminApplication import AdminApplication
    from model.watermark_verification import WatermarkVerification
    from model.download_token import DownloadToken

    models = [
        AdmAccount, AdmInfo, AdmNav, Announcement, Application, ChatMessage,
        DownloadRecord, EmployeeNotification, EmployeeAccount, EmployeeInfo,
        EmployeeNav, FriendRequest, LogInfo, RasterData, Shp,
        RecallProposal, AdminApplication, WatermarkVerification, DownloadToken
    ]

    with app.app_context():
        for model in models:
            try:
                engine = db.session.get_bind(mapper=model)
                model.__table__.create(bind=engine, checkfirst=True)
            except Exception as e:
                app.logger.warning(f"Skip table bootstrap for {model.__tablename__}: {e}")

def create_app():
    app = Flask(__name__)

    # Load configuration from config.py
    from config import get_config
    app.config.from_object(get_config())

    # Convert seconds to timedelta for JWT
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(seconds=app.config['JWT_ACCESS_TOKEN_EXPIRES'])
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(seconds=app.config['JWT_REFRESH_TOKEN_EXPIRES'])

    # Extensions initialization
    db.init_app(app)
    limiter.init_app(app)
    Migrate(app, db)
    JWTManager(app)
    _bootstrap_runtime_schema(app)

    # CORS configuration
    cors_origins = app.config['CORS_ORIGINS']
    CORS(app,
         origins=[o.strip() for o in cors_origins],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
         expose_headers=["Content-Disposition"],
         supports_credentials=True
    )

    # Swagger (optional — installed via `pip install flasgger`)
    if _has_flasgger:
        swagger_config = {
            "headers": [],
            "specs": [
                {
                    "endpoint": 'apispec',
                    "route": '/apispec.json',
                    "rule_filter": lambda rule: True,
                    "model_filter": lambda tag: True,
                }
            ],
            "static_url_path": "/flasgger_static",
            "swagger_ui": True,
            "specs_route": "/apidocs/"
        }
        Swagger(app, config=swagger_config)

    # Directory auto-creation
    for folder_key in ['UPLOAD_FOLDER', 'WATERMARK_FOLDER', 'EXTRACTED_FOLDER']:
        folder_path = app.config.get(folder_key)
        if folder_path and not os.path.exists(folder_path):
            try:
                os.makedirs(folder_path, exist_ok=True)
            except Exception as e:
                app.logger.error(f"Failed to create {folder_key} at {folder_path}: {e}")

    # Request size limit (100MB for file uploads)
    app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

    # Global Error Handlers
    @app.errorhandler(400)
    def handle_400_error(e):
        return jsonify({"status": False, "msg": "请求参数错误"}), 400

    @app.errorhandler(401)
    def handle_401_error(e):
        return jsonify({"status": False, "msg": "未授权访问"}), 401

    @app.errorhandler(403)
    def handle_403_error(e):
        return jsonify({"status": False, "msg": "禁止访问"}), 403

    @app.errorhandler(404)
    def handle_404_error(e):
        return jsonify({"status": False, "msg": "请求的资源不存在"}), 404

    @app.errorhandler(413)
    def handle_413_error(e):
        return jsonify({"status": False, "msg": "上传文件过大"}), 413

    @app.errorhandler(429)
    def handle_429_error(e):
        return jsonify({"status": False, "msg": "请求过于频繁，请稍后重试"}), 429

    @app.errorhandler(500)
    def handle_500_error(e):
        app.logger.error(f"Internal Server Error: {e}")
        return jsonify({"status": False, "msg": "服务器内部错误，请稍后重试"}), 500

    @app.errorhandler(Exception)
    def handle_unhandled_exception(e):
        app.logger.error(f"Unhandled exception: {e}", exc_info=True)
        return jsonify({"status": False, "msg": "服务器内部错误，请稍后重试"}), 500

    api = Api(app)
    
    # Import and Register Resources
    from resource.common_resource import RegisterResource, LoginResource, LogoutResource, RefreshTokenResource
    from resource.nav_resource import NavTreeResource, NavListResource
    from resource.adm_resource import (
        GetEmpInfoListResource, AddEmployeeResource, EmployeeDetailsResource,
        EmployeeUpdateResource, AdminDeleteEmployeeResource, AccountCreateResource
    )
    from resource.shp_data_resource import ShpDataListResource, ShpDataByIdResource, VectorDataViewingResource, RasterDataViewingResource, MapSearchResource
    from resource.application_resource import (
        SubmitApplicationResource, GetApplicationsResource, ApprovedApplicationsResource,
        Adm1GetApplicationsResource, Adm2GetApprovedResource,
        Adm1PassResource, Adm1FailResource, Adm2PassResource, Adm2FailResource,
        BatchReviewResource, ReReviewResource, Adm3AdditionalReviewResource,
        Adm1GetShpApplicationsResource, Adm1GetRasterApplicationsResource,
        ApplicationQRCodeResource, ApplicationQRCodeImageResource, ApplicationDetailResource, AllApplicationsResource
    )
    from resource.watermark_resource import (
        GenerateWatermarkResource, EmbeddingWatermarkResource, VectorExtractResource,
        Adm1GetGenerateWatermarkApplications, Adm2GetEmbeddingWatermarkApplications,
        UploadOriginalWatermarkResource, UploadExtractedWatermarkResource,
        UploadOriAndExtWatermarkResource, GetOriginalWatermarkResource
    )
    from resource.raster_resource import (
        RasterPreviewResource, RasterTilesResource, RasterEmbedDispatchResource, 
        CRMarkEmbedResource, CRMarkRecoverResource, CRMarkDecodeResource,
        Adm1GetRasterApplicationsGenerateWatermark, GenerateRasterWatermarkResource
    )
    from resource.download_file_resource import EmpDownloadZipResource, RecordDownloadResource, RequestDownloadTokenResource, TokenDownloadResource
    from resource.upload_data_resource import ShpDataUploadResource, RasterDataUploadResource
    from resource.log_resource import SystemLogResource
    from resource.dashboard_resource import AdminDashboardResource, EmployeeDashboardResource
    from resource.announcement_resource import AnnouncementResource
    from resource.profile_resource import EmployeeProfileResource, EmployeePhotoResource, EmployeePasswordResource
    from resource.collaboration_resource import (
        ProtectedResource, AdminSendNotificationResource,
        EmployeeNotificationsResource, EmployeeNotificationReadResource, EmployeeMyLogsResource,
        AdminAnnouncementManageResource, ChatConversationsResource, ChatMessagesResource,
        ChatMarkReadResource, ChatSearchUsersResource, ChatAddFriendResource,
        ChatFriendRequestsResource, ChatFriendRespondResource, ChatSendResource,
        BatchReviewFailedExportResource, AdminUserListResource
    )
    from resource.recall_resource import (
        RecallListResource, RecallCreateResource, RecallVoteResource,
        RecallDetailResource, RecallCloseResource, RecallHistoryResource
    )
    from resource.admin_application_resource import (
        AdminApplicationEligibilityResource, AdminApplicationSubmitResource,
        AdminApplicationMyResource, AdminApplicationListResource,
        AdminApplicationDetailResource, AdminApplicationVoteResource, AdminApplicationCloseResource
    )

    # --- Security Headers ---
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        if not app.config.get('DEBUG'):
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response

    # --- Routes ---

    # Health & Auth
    from resource.health_resource import HealthCheckResource
    api.add_resource(HealthCheckResource, '/api/health')
    api.add_resource(RegisterResource, '/api/register')
    api.add_resource(RegisterResource, '/api/register')
    api.add_resource(LoginResource, '/api/login')
    api.add_resource(LogoutResource, '/api/logout')
    api.add_resource(RefreshTokenResource, '/api/refresh-token')
    api.add_resource(ProtectedResource, '/api/protected')
    
    # Navigation
    api.add_resource(NavTreeResource, '/api/admin/nav/tree', '/api/employee/nav/tree')
    api.add_resource(NavListResource, '/api/admin/nav/list', '/api/employee/nav/list')
    
    # Data Viewing
    api.add_resource(VectorDataViewingResource, '/api/vector_data_viewing')
    api.add_resource(RasterDataViewingResource, '/api/raster_data_viewing')
    api.add_resource(ShpDataListResource, '/api/data_viewing/pageList', '/api/data_viewing')
    api.add_resource(ShpDataByIdResource, '/api/data_viewing/getById')
    api.add_resource(MapSearchResource, '/api/map/search', '/api/geocoding/search')
    
    # Applications
    api.add_resource(SubmitApplicationResource, '/api/submit_application')
    api.add_resource(GetApplicationsResource, '/api/get_applications')
    api.add_resource(ApprovedApplicationsResource, '/api/get_approved_applications')
    api.add_resource(AllApplicationsResource, '/api/applications')
    api.add_resource(ApplicationDetailResource, '/api/applications/<int:application_id>')
    api.add_resource(ApplicationQRCodeResource, '/api/applications/<int:application_id>/qrcode')
    api.add_resource(ApplicationQRCodeImageResource, '/api/applications/<int:application_id>/qrcode/image')
    
    # Admin Application Management
    api.add_resource(GetEmpInfoListResource, '/api/adm/get_emp_info_list', '/api/admin/get_employee_info')
    api.add_resource(AddEmployeeResource, '/api/adm/add_employee')
    api.add_resource(AccountCreateResource, '/api/account/create')
    api.add_resource(EmployeeDetailsResource, '/api/employee/details/<string:employee_number>')
    api.add_resource(EmployeeUpdateResource, '/api/employee/<string:employee_number>')
    api.add_resource(AdminDeleteEmployeeResource, '/api/admin/employee/<string:employee_number>')
    api.add_resource(Adm1GetApplicationsResource, '/api/adm1_get_applications')
    api.add_resource(Adm1GetShpApplicationsResource, '/api/adm1_get_shp_applications')
    api.add_resource(Adm1GetRasterApplicationsResource, '/api/adm1_get_raster_applications')
    api.add_resource(Adm2GetApprovedResource, '/api/adm2_get_approved')
    api.add_resource(Adm1PassResource, '/api/adm1_pass')
    api.add_resource(Adm1FailResource, '/api/adm1_fail')
    api.add_resource(Adm2PassResource, '/api/adm2_pass')
    api.add_resource(Adm2FailResource, '/api/adm2_fail')
    api.add_resource(Adm3AdditionalReviewResource, '/api/adm3_additional_review')
    api.add_resource(BatchReviewResource, '/api/admin/batch_review')
    api.add_resource(ReReviewResource, '/api/admin/re_review')
    api.add_resource(BatchReviewFailedExportResource, '/api/admin/batch_review_failed_export')
    
    # Watermark
    api.add_resource(Adm1GetGenerateWatermarkApplications, '/api/adm1_get_applications_generate_watermark')
    api.add_resource(GenerateWatermarkResource, '/api/generate_watermark')
    api.add_resource(Adm2GetEmbeddingWatermarkApplications, '/api/adm2_embedding_watermark_applications')
    api.add_resource(EmbeddingWatermarkResource, '/api/embedding_watermark')
    api.add_resource(VectorExtractResource, '/api/vector/extract')
    api.add_resource(UploadOriginalWatermarkResource, '/api/upload_original_watermark')
    api.add_resource(UploadExtractedWatermarkResource, '/api/upload_extracted_watermark')
    api.add_resource(UploadOriAndExtWatermarkResource, '/api/upload/ori&ext_watermark')
    api.add_resource(GetOriginalWatermarkResource, '/api/get_original_watermark')
    
    # Raster
    api.add_resource(Adm1GetRasterApplicationsGenerateWatermark, '/api/adm1_get_raster_applications_generate_watermark')
    api.add_resource(GenerateRasterWatermarkResource, '/api/generate_raster_watermark')
    api.add_resource(RasterPreviewResource, '/api/raster/preview')
    api.add_resource(RasterTilesResource, '/api/raster_tiles/<int:data_id>/<int:z>/<int:x>/<int:y>.png')
    api.add_resource(RasterEmbedDispatchResource, '/api/admin/embed_dispatch')
    api.add_resource(CRMarkEmbedResource, '/api/crmark/embed')
    api.add_resource(CRMarkRecoverResource, '/api/crmark/recover')
    api.add_resource(CRMarkDecodeResource, '/api/crmark/decode')
    
    # Download
    api.add_resource(EmpDownloadZipResource, '/api/emp_download_zip')
    api.add_resource(RecordDownloadResource, '/api/record_download_file')
    api.add_resource(RequestDownloadTokenResource, '/api/request_download_token')
    api.add_resource(TokenDownloadResource, '/api/download/<string:download_token>')
    api.add_resource(ShpDataUploadResource, '/api/upload_shp_data')
    api.add_resource(RasterDataUploadResource, '/api/upload_raster_data')
    
    # Logs & Dashboard
    api.add_resource(SystemLogResource, '/api/admin/logs')
    api.add_resource(AdminDashboardResource, '/api/admin/dashboard')
    api.add_resource(EmployeeDashboardResource, '/api/employee/dashboard')
    api.add_resource(AnnouncementResource, '/api/announcements')
    api.add_resource(AdminAnnouncementManageResource, '/api/admin/announcements')
    api.add_resource(AdminSendNotificationResource, '/api/admin/notifications/send')
    api.add_resource(EmployeeNotificationsResource, '/api/employee/notifications')
    api.add_resource(EmployeeNotificationReadResource, '/api/employee/notifications/<int:notification_id>/read')
    api.add_resource(EmployeeMyLogsResource, '/api/employee/my_logs')
    api.add_resource(ChatConversationsResource, '/api/chat/conversations')
    api.add_resource(ChatMessagesResource, '/api/chat/messages')
    api.add_resource(ChatMarkReadResource, '/api/chat/mark_read')
    api.add_resource(ChatSearchUsersResource, '/api/chat/search_users')
    api.add_resource(ChatAddFriendResource, '/api/chat/add_friend')
    api.add_resource(ChatFriendRequestsResource, '/api/chat/friend_requests')
    api.add_resource(ChatFriendRespondResource, '/api/chat/friend_respond')
    api.add_resource(ChatSendResource, '/api/chat/send')
    api.add_resource(AdminUserListResource, '/api/admin/users')

    # Profile
    api.add_resource(EmployeeProfileResource, '/api/employee/profile')
    api.add_resource(EmployeePhotoResource, '/api/employee/photo/<string:employee_number>')
    api.add_resource(EmployeePasswordResource, '/api/employee/password')

    # Recall Proposal
    api.add_resource(RecallListResource, '/api/recall/list')
    api.add_resource(RecallCreateResource, '/api/recall/create')
    api.add_resource(RecallVoteResource, '/api/recall/<int:proposal_id>/vote')
    api.add_resource(RecallDetailResource, '/api/recall/<int:proposal_id>')
    api.add_resource(RecallCloseResource, '/api/recall/<int:proposal_id>/close')
    api.add_resource(RecallHistoryResource, '/api/recall/history/<int:application_id>')

    # Admin Application
    api.add_resource(AdminApplicationEligibilityResource, '/api/admin-application/eligibility')
    api.add_resource(AdminApplicationSubmitResource, '/api/admin-application/submit')
    api.add_resource(AdminApplicationMyResource, '/api/admin-application/my')
    api.add_resource(AdminApplicationListResource, '/api/admin-application/list')
    api.add_resource(AdminApplicationDetailResource, '/api/admin-application/<int:application_id>')
    api.add_resource(AdminApplicationVoteResource, '/api/admin-application/<int:application_id>/vote')
    api.add_resource(AdminApplicationCloseResource, '/api/admin-application/<int:application_id>/close')

    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5003))
    app.run(debug=app.config.get('DEBUG', False), port=port, use_reloader=False)
