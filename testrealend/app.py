import os
import platform

# Work around Windows WMI hangs triggered by platform.uname() / platform.machine()
# during imports (SQLAlchemy, Alembic, prometheus_client, etc.) on some environments.
if os.name == "nt":
    try:
        _machine = os.environ.get("PROCESSOR_ARCHITECTURE", "AMD64")
        platform.machine = lambda: _machine
        _uname_result = platform.uname_result(
            system="Windows", node="localhost", release="10", version="", machine=_machine
        )
        platform.uname = lambda: _uname_result
    except Exception:
        pass

from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_restful import Api

from extension.extension import db, limiter

try:
    from flasgger import Swagger  # type: ignore[import-not-found]

    _has_flasgger = True
except ImportError:
    _has_flasgger = False

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))


def _bootstrap_runtime_schema(app):
    """
    Ensure core tables exist so first-time deployments don't fail with 500 due
    to missing tables.
    """
    from model.Adm_Account import AdmAccount
    from model.Adm_Info import AdmInfo
    from model.Adm_Nav import AdmNav
    from model.AdmAccountPermission import AdmAccountPermissions
    from model.AdminApplication import AdminApplication
    from model.Announcement import Announcement
    from model.Application import Application
    from model.ChatMessage import ChatMessage
    from model.Download_Record import DownloadRecord
    from model.download_token import DownloadToken
    from model.Embed_File_Record import EmbedFileRecord
    from model.Employee_Account import EmployeeAccount
    from model.Employee_Info import EmployeeInfo
    from model.Employee_Nav import EmployeeNav
    from model.EmployeeNotification import EmployeeNotification
    from model.Extract_Helper import ExtractHelper
    from model.FriendRequest import FriendRequest
    from model.Log_Info import LogInfo
    from model.Permission import Permission
    from model.Raster_Data import RasterData
    from model.RecallProposal import RecallProposal
    from model.SendFileRecord import SendFileRecord
    from model.Shp_Data import Shp
    from model.TokenBlacklist import TokenBlacklist
    from model.watermark_verification import WatermarkVerification

    models = [
        AdmAccount,
        AdmInfo,
        AdmNav,
        Announcement,
        Application,
        ChatMessage,
        DownloadRecord,
        EmployeeNotification,
        EmployeeAccount,
        EmployeeInfo,
        EmployeeNav,
        FriendRequest,
        LogInfo,
        RasterData,
        Shp,
        RecallProposal,
        AdminApplication,
        WatermarkVerification,
        DownloadToken,
        TokenBlacklist,
        Permission,
        AdmAccountPermissions,
        EmbedFileRecord,
        ExtractHelper,
        SendFileRecord,
    ]

    # ShpFile and MysqlShpFile use geoalchemy2/mysql-specific types — import gracefully
    try:
        from model.Shp_File import ShpFile

        models.append(ShpFile)
    except ImportError:
        pass
    try:
        from model.mysqlshpio import MysqlShpFile

        models.append(MysqlShpFile)
    except ImportError:
        pass

    # Create tables that don't exist yet (idempotent via create_all)
    with app.app_context():
        from extension.extension import db

        try:
            # Only create tables if they don't already exist
            from sqlalchemy import inspect

            existing = inspect(db.engine).get_table_names()
            for model in models:
                table_name = model.__tablename__
                if table_name not in existing:
                    db.create_all()
                    app.logger.info(f"Created missing table: {table_name}")
                    break
            else:
                app.logger.info("All core tables present")
        except Exception as e:
            app.logger.error(f"Table check failed (DB may be unreachable): {e}")


def _startup_health_check(app):
    """Verify critical services are reachable and print status to console."""
    results = []

    # Database check
    try:
        from extension.extension import db

        with app.app_context():
            db.session.execute(db.text("SELECT 1"))
        results.append(("  Database (MySQL)", True, "connected"))
    except Exception as e:
        results.append(("  Database (MySQL)", False, str(e)))

    # Redis check
    try:
        from utils.cache import get_redis

        r = get_redis()
        if r:
            r.ping()
            results.append(("  Redis", True, "connected"))
        else:
            results.append(("  Redis", False, "client not initialized (not critical)"))
    except Exception as e:
        results.append(("  Redis", False, str(e)))

    # Print health check results
    print("\n" + "=" * 60)
    print("  STARTUP HEALTH CHECK")
    print("=" * 60)
    all_ok = True
    for name, ok, detail in results:
        status = "OK" if ok else "WARN"
        if not ok:
            all_ok = False
        print(f"[{status}] {name}: {detail}")
    print("=" * 60)

    if not all_ok:
        print("WARNING: Some services are unavailable. The server will start but may return 500 errors.")
    print()


def create_app():
    app = Flask(__name__)

    # Load configuration from config.py
    from config import get_config

    app.config.from_object(get_config())

    # Convert seconds to timedelta for JWT
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(seconds=app.config["JWT_ACCESS_TOKEN_EXPIRES"])
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(seconds=app.config["JWT_REFRESH_TOKEN_EXPIRES"])

    # Configure logging
    from utils.logging_config import setup_logging

    setup_logging(app)

    # Extensions initialization
    db.init_app(app)
    limiter.init_app(app)
    Migrate(app, db)
    jwt = JWTManager(app)

    # Token blocklist check
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        try:
            from model.TokenBlacklist import TokenBlacklist

            jti = jwt_payload.get("jti")
            return TokenBlacklist.query.filter_by(jti=jti).first() is not None
        except Exception:
            return False

    _bootstrap_runtime_schema(app)

    # Initialize Redis cache
    from utils.cache import init_cache

    init_cache(app)

    # Initialize Prometheus metrics
    from utils.metrics import setup_metrics

    setup_metrics(app)

    # Initialize WebSocket (Socket.IO)
    from utils.websocket import init_socketio

    socketio = init_socketio(app)
    app.socketio = socketio

    # Initialize per-user rate limiter
    from utils.user_limiter import init_user_limiter

    init_user_limiter(app)

    # CORS configuration
    cors_origins = app.config["CORS_ORIGINS"]
    CORS(
        app,
        origins=[o.strip() for o in cors_origins],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
        expose_headers=["Content-Disposition"],
        supports_credentials=True,
    )

    # Swagger (optional — installed via `pip install flasgger`)
    if _has_flasgger:
        swagger_config = {
            "headers": [],
            "specs": [
                {
                    "endpoint": "apispec",
                    "route": "/apispec.json",
                    "rule_filter": lambda rule: True,
                    "model_filter": lambda tag: True,
                }
            ],
            "static_url_path": "/flasgger_static",
            "swagger_ui": True,
            "specs_route": "/apidocs/",
        }
        Swagger(app, config=swagger_config)

    # Directory auto-creation
    for folder_key in ["UPLOAD_FOLDER", "WATERMARK_FOLDER", "EXTRACTED_FOLDER"]:
        folder_path = app.config.get(folder_key)
        if folder_path and not os.path.exists(folder_path):
            try:
                os.makedirs(folder_path, exist_ok=True)
            except Exception as e:
                app.logger.error(f"Failed to create {folder_key} at {folder_path}: {e}")

    # Request size limit (100MB for file uploads)
    app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

    # Startup health check — verify DB, Redis, etc. before serving requests
    _startup_health_check(app)

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
        import sys
        import traceback

        app.logger.error(f"Internal Server Error: {e}")
        traceback.print_exc(file=sys.stderr)
        return jsonify({"status": False, "msg": "服务器内部错误，请稍后重试"}), 500

    @app.errorhandler(Exception)
    def handle_unhandled_exception(e):
        import sys
        import traceback

        app.logger.error(f"Unhandled exception: {e}", exc_info=True)
        traceback.print_exc(file=sys.stderr)
        return jsonify({"status": False, "msg": "服务器内部错误，请稍后重试"}), 500

    api = Api(app)

    # Import and Register Resources
    from resource.adm_resource import (
        AccountCreateResource,
        AddEmployeeResource,
        AdminDeleteEmployeeResource,
        EmployeeDetailsResource,
        EmployeeUpdateResource,
        GetEmpInfoListResource,
    )
    from resource.admin_application_resource import (
        AdminApplicationCloseResource,
        AdminApplicationDetailResource,
        AdminApplicationEligibilityResource,
        AdminApplicationListResource,
        AdminApplicationMyResource,
        AdminApplicationSubmitResource,
        AdminApplicationVoteResource,
    )
    from resource.announcement_resource import AnnouncementResource
    from resource.application_resource import (
        Adm1FailResource,
        Adm1GetApplicationsResource,
        Adm1GetRasterApplicationsResource,
        Adm1GetShpApplicationsResource,
        Adm1PassResource,
        Adm2FailResource,
        Adm2GetApprovedResource,
        Adm2PassResource,
        Adm3AdditionalReviewResource,
        AllApplicationsResource,
        ApplicationDetailResource,
        ApplicationQRCodeImageResource,
        ApplicationQRCodeResource,
        ApprovedApplicationsResource,
        BatchReviewResource,
        GetApplicationsResource,
        ReReviewResource,
        SubmitApplicationResource,
        WithdrawApplicationResource,
    )
    from resource.collaboration_resource import (
        AdminAnnouncementManageResource,
        AdminSendNotificationResource,
        AdminUserListResource,
        BatchReviewFailedExportResource,
        ChatAddFriendResource,
        ChatConversationsResource,
        ChatFriendRequestsResource,
        ChatFriendRespondResource,
        ChatMarkReadResource,
        ChatMessagesResource,
        ChatSearchUsersResource,
        ChatSendResource,
        EmployeeMyLogsResource,
        EmployeeNotificationReadResource,
        EmployeeNotificationsResource,
        ProtectedResource,
    )
    from resource.common_resource import (
        BenchmarkResultsResource,
        LoginResource,
        LogoutResource,
        RefreshTokenResource,
        RegisterResource,
    )
    from resource.dashboard_resource import AdminDashboardResource, EmployeeDashboardResource
    from resource.download_file_resource import (
        EmpDownloadZipResource,
        RecordDownloadResource,
        RequestDownloadTokenResource,
        TokenDownloadResource,
    )
    from resource.log_resource import SystemLogResource
    from resource.nav_resource import NavListResource, NavTreeResource
    from resource.profile_resource import EmployeePasswordResource, EmployeePhotoResource, EmployeeProfileResource
    from resource.raster_resource import (
        Adm1GetRasterApplicationsGenerateWatermark,
        CRMarkDecodeResource,
        CRMarkEmbedResource,
        CRMarkRecoverResource,
        GenerateRasterWatermarkResource,
        RasterEmbedDispatchResource,
        RasterGenerateTilesResource,
        RasterPreviewResource,
        RasterTilesResource,
    )
    from resource.recall_resource import (
        RecallCloseResource,
        RecallCreateResource,
        RecallDetailResource,
        RecallHistoryResource,
        RecallListResource,
        RecallRestoreResource,
        RecallVoteResource,
    )
    from resource.shp_data_resource import (
        MapSearchResource,
        RasterDataViewingResource,
        ShpDataByIdResource,
        ShpDataListResource,
        VectorDataViewingResource,
    )
    from resource.upload_data_resource import RasterDataUploadResource, ShpDataUploadResource
    from resource.watermark_embed_resource import Adm2GetEmbeddingWatermarkApplications, EmbeddingWatermarkResource
    from resource.watermark_extract_resource import QRCodeDecodeResource, VectorExtractResource
    from resource.watermark_generate_resource import Adm1GetGenerateWatermarkApplications, GenerateWatermarkResource
    from resource.watermark_upload_resource import (
        BatchEmbedWatermarkResource,
        BatchGenerateWatermarkResource,
        GetOriginalWatermarkResource,
        UploadExtractedWatermarkResource,
        UploadOriAndExtWatermarkResource,
        UploadOriginalWatermarkResource,
        WatermarkPreviewResource,
        WatermarkVerificationRecordsResource,
    )

    # --- Security Headers ---
    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if not app.config.get("DEBUG"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # --- Routes ---

    # Health & Auth
    from resource.health_resource import HealthCheckResource

    api.add_resource(HealthCheckResource, "/api/health")
    api.add_resource(RegisterResource, "/api/register")
    api.add_resource(LoginResource, "/api/login")
    api.add_resource(LogoutResource, "/api/logout")
    api.add_resource(RefreshTokenResource, "/api/refresh-token")
    api.add_resource(BenchmarkResultsResource, "/api/benchmark/results")
    api.add_resource(ProtectedResource, "/api/protected")

    # Navigation
    api.add_resource(NavTreeResource, "/api/admin/nav/tree", "/api/employee/nav/tree")
    api.add_resource(NavListResource, "/api/admin/nav/list", "/api/employee/nav/list")

    # Data Viewing
    api.add_resource(VectorDataViewingResource, "/api/vector_data_viewing")
    api.add_resource(RasterDataViewingResource, "/api/raster_data_viewing")
    api.add_resource(ShpDataListResource, "/api/data_viewing/pageList", "/api/data_viewing")
    api.add_resource(ShpDataByIdResource, "/api/data_viewing/getById")
    api.add_resource(MapSearchResource, "/api/map/search", "/api/geocoding/search")

    # Applications
    api.add_resource(SubmitApplicationResource, "/api/submit_application")
    api.add_resource(WithdrawApplicationResource, "/api/applications/<int:application_id>/withdraw")
    api.add_resource(GetApplicationsResource, "/api/get_applications")
    api.add_resource(ApprovedApplicationsResource, "/api/get_approved_applications")
    api.add_resource(AllApplicationsResource, "/api/applications")
    api.add_resource(ApplicationDetailResource, "/api/applications/<int:application_id>")
    api.add_resource(ApplicationQRCodeResource, "/api/applications/<int:application_id>/qrcode")
    api.add_resource(ApplicationQRCodeImageResource, "/api/applications/<int:application_id>/qrcode/image")

    # Admin Application Management
    api.add_resource(GetEmpInfoListResource, "/api/adm/get_emp_info_list", "/api/admin/get_employee_info")
    api.add_resource(AddEmployeeResource, "/api/adm/add_employee")
    api.add_resource(AccountCreateResource, "/api/account/create")
    api.add_resource(EmployeeDetailsResource, "/api/employee/details/<string:employee_number>")
    api.add_resource(EmployeeUpdateResource, "/api/employee/<string:employee_number>")
    api.add_resource(AdminDeleteEmployeeResource, "/api/admin/employee/<string:employee_number>")
    api.add_resource(Adm1GetApplicationsResource, "/api/adm1_get_applications")
    api.add_resource(Adm1GetShpApplicationsResource, "/api/adm1_get_shp_applications")
    api.add_resource(Adm1GetRasterApplicationsResource, "/api/adm1_get_raster_applications")
    api.add_resource(Adm2GetApprovedResource, "/api/adm2_get_approved")
    api.add_resource(Adm1PassResource, "/api/adm1_pass")
    api.add_resource(Adm1FailResource, "/api/adm1_fail")
    api.add_resource(Adm2PassResource, "/api/adm2_pass")
    api.add_resource(Adm2FailResource, "/api/adm2_fail")
    api.add_resource(Adm3AdditionalReviewResource, "/api/adm3_additional_review")
    api.add_resource(BatchReviewResource, "/api/admin/batch_review")
    api.add_resource(ReReviewResource, "/api/admin/re_review")
    api.add_resource(BatchReviewFailedExportResource, "/api/admin/batch_review_failed_export")

    # Watermark
    api.add_resource(Adm1GetGenerateWatermarkApplications, "/api/adm1_get_applications_generate_watermark")
    api.add_resource(GenerateWatermarkResource, "/api/generate_watermark")
    api.add_resource(Adm2GetEmbeddingWatermarkApplications, "/api/adm2_embedding_watermark_applications")
    api.add_resource(EmbeddingWatermarkResource, "/api/embedding_watermark")
    api.add_resource(VectorExtractResource, "/api/vector/extract")
    api.add_resource(QRCodeDecodeResource, "/api/qrcode/decode")
    api.add_resource(UploadOriginalWatermarkResource, "/api/upload_original_watermark")
    api.add_resource(UploadExtractedWatermarkResource, "/api/upload_extracted_watermark")
    api.add_resource(UploadOriAndExtWatermarkResource, "/api/upload/ori&ext_watermark")
    api.add_resource(GetOriginalWatermarkResource, "/api/get_original_watermark")
    api.add_resource(WatermarkVerificationRecordsResource, "/api/watermark/verification_records")
    api.add_resource(WatermarkPreviewResource, "/api/watermark/preview")
    api.add_resource(BatchGenerateWatermarkResource, "/api/watermark/batch_generate")
    api.add_resource(BatchEmbedWatermarkResource, "/api/watermark/batch_embed")

    # Raster
    api.add_resource(Adm1GetRasterApplicationsGenerateWatermark, "/api/adm1_get_raster_applications_generate_watermark")
    api.add_resource(GenerateRasterWatermarkResource, "/api/generate_raster_watermark")
    api.add_resource(RasterPreviewResource, "/api/raster/preview")
    api.add_resource(RasterTilesResource, "/api/raster_tiles/<int:data_id>/<int:z>/<int:x>/<int:y>.png")
    api.add_resource(RasterGenerateTilesResource, "/api/raster/generate_tiles")
    api.add_resource(RasterEmbedDispatchResource, "/api/admin/embed_dispatch")
    api.add_resource(CRMarkEmbedResource, "/api/crmark/embed")
    api.add_resource(CRMarkRecoverResource, "/api/crmark/recover")
    api.add_resource(CRMarkDecodeResource, "/api/crmark/decode")

    # Download
    api.add_resource(EmpDownloadZipResource, "/api/emp_download_zip")
    api.add_resource(RecordDownloadResource, "/api/record_download_file")
    api.add_resource(RequestDownloadTokenResource, "/api/request_download_token")
    api.add_resource(TokenDownloadResource, "/api/download/<string:download_token>")
    api.add_resource(ShpDataUploadResource, "/api/upload_shp_data")
    api.add_resource(RasterDataUploadResource, "/api/upload_raster_data")

    # Logs & Dashboard
    api.add_resource(SystemLogResource, "/api/admin/logs")
    api.add_resource(AdminDashboardResource, "/api/admin/dashboard")
    api.add_resource(EmployeeDashboardResource, "/api/employee/dashboard")
    api.add_resource(AnnouncementResource, "/api/announcements")
    api.add_resource(AdminAnnouncementManageResource, "/api/admin/announcements")
    api.add_resource(AdminSendNotificationResource, "/api/admin/notifications/send")
    api.add_resource(EmployeeNotificationsResource, "/api/employee/notifications")
    api.add_resource(EmployeeNotificationReadResource, "/api/employee/notifications/<int:notification_id>/read")
    api.add_resource(EmployeeMyLogsResource, "/api/employee/my_logs", "/api/employee/my-logs")
    api.add_resource(ChatConversationsResource, "/api/chat/conversations")
    api.add_resource(ChatMessagesResource, "/api/chat/messages")
    api.add_resource(ChatMarkReadResource, "/api/chat/mark_read", "/api/chat/mark-read")
    api.add_resource(ChatSearchUsersResource, "/api/chat/search_users", "/api/chat/search-users")
    api.add_resource(ChatAddFriendResource, "/api/chat/add_friend", "/api/chat/add-friend")
    api.add_resource(ChatFriendRequestsResource, "/api/chat/friend_requests", "/api/chat/friend-requests")
    api.add_resource(ChatFriendRespondResource, "/api/chat/friend_respond", "/api/chat/friend-respond")
    api.add_resource(ChatSendResource, "/api/chat/send")
    api.add_resource(AdminUserListResource, "/api/admin/users")

    # Profile
    api.add_resource(EmployeeProfileResource, "/api/employee/profile")
    api.add_resource(EmployeePhotoResource, "/api/employee/photo/<string:employee_number>")
    api.add_resource(EmployeePasswordResource, "/api/employee/password")

    # Recall Proposal
    api.add_resource(RecallListResource, "/api/recall/list")
    api.add_resource(RecallCreateResource, "/api/recall/create")
    api.add_resource(RecallVoteResource, "/api/recall/<int:proposal_id>/vote")
    api.add_resource(RecallDetailResource, "/api/recall/<int:proposal_id>")
    api.add_resource(RecallCloseResource, "/api/recall/<int:proposal_id>/close")
    api.add_resource(RecallHistoryResource, "/api/recall/history/<int:application_id>")
    api.add_resource(RecallRestoreResource, "/api/recall/restore")

    # Admin Application
    api.add_resource(AdminApplicationEligibilityResource, "/api/admin-application/eligibility")
    api.add_resource(AdminApplicationSubmitResource, "/api/admin-application/submit")
    api.add_resource(AdminApplicationMyResource, "/api/admin-application/my")
    api.add_resource(AdminApplicationListResource, "/api/admin-application/list")
    api.add_resource(AdminApplicationDetailResource, "/api/admin-application/<int:application_id>")
    api.add_resource(AdminApplicationVoteResource, "/api/admin-application/<int:application_id>/vote")
    api.add_resource(AdminApplicationCloseResource, "/api/admin-application/<int:application_id>/close")

    return app


import subprocess as _subprocess


def _kill_stale_on_port(port):
    """Kill any process already listening on the target port so we can bind."""
    if os.name != "nt":
        return
    import re

    try:
        result = _subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=10)
        for line in result.stdout.splitlines():
            m = re.search(rf":({port})\s+.*LISTENING\s+(\d+)", line)
            if m:
                pid = m.group(2)
                if pid and pid.isdigit() and int(pid) != os.getpid():
                    _subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
                    print(f"Killed stale process (PID {pid}) occupying port {port}")
    except BaseException:
        pass


app = create_app()

if __name__ == "__main__":
    import time as _time

    port = int(os.environ.get("PORT", 5003))

    # Retry loop: Windows + Python 3.12.8 can fire spurious KeyboardInterrupt
    # at nearly any point during startup (sleep, subprocess, module imports).
    # Instead of crashing, we retry a few times.
    for _attempt in range(5):
        _server_started = False
        try:
            _kill_stale_on_port(port)
            _time.sleep(0.5)

            port_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".backend-port")
            try:
                with open(port_file, "w") as f:
                    f.write(str(port))
            except Exception:
                pass

            print("")
            print("=" * 60)
            print("  SERVER STARTING")
            print(f"  Backend:  http://127.0.0.1:{port}")
            print(f"  API Doc:  http://127.0.0.1:{port}/apidocs/")
            print(f"  Health:   http://127.0.0.1:{port}/api/health")
            print("  Frontend: http://localhost:5173")
            print("=" * 60)
            print("  Press CTRL+C to stop")
            print("")

            # SocketIO with async_mode="threading" works on top of Flask's built-in server.
            # socketio.run() is unreliable on Windows (can return silently), so we always
            # use app.run() — SocketIO long-polling works fine through the regular WSGI stack.
            _server_started = True
            app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
            break
        except KeyboardInterrupt:
            if _server_started:
                print("\n * Server stopped by user (Ctrl+C)")
                break
            # Spurious interrupt during pre-flight — retry
        except BaseException:
            pass
        _time.sleep(1)
    else:
        print(" * Failed to start after 5 attempts.")
