import logging
from datetime import UTC, datetime, timedelta

from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource
from sqlalchemy import and_, case, func, or_

from extension.extension import db
from model.Adm_Account import AdmAccount
from model.Adm_Info import AdmInfo
from model.AdminApplication import AdminApplication
from model.Application import Application
from model.Download_Record import DownloadRecord
from model.Employee_Account import EmployeeAccount
from model.Log_Info import LogInfo
from model.Raster_Data import RasterData
from model.RecallProposal import RecallProposal
from model.Shp_Data import Shp
from utils.cache import cached
from utils.required import admin_required, is_admin_role
from utils.user_limiter import relaxed_limit


def _day_window(days_ago):
    end = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1 - days_ago)
    start = end - timedelta(days=1)
    return start, end


def _batch_day_counts(model, timestamp_col, days=14, extra_filters=None):
    """一次 GROUP BY 查询拿到 N 天每天的计数，替代 N 次单独 count。"""
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start = today_start - timedelta(days=days - 1)
    # func.date() renders DATE(col) on MySQL and date(col) on SQLite: both
    # yield a calendar day. cast(col, Date) crashed SQLite (the CAST result is
    # numeric for SQLite's NUMERIC affinity there, and SQLAlchemy's Date result
    # processor then raised "fromisoformat: argument must be str").
    date_col = func.date(timestamp_col)
    q = db.session.query(date_col, func.count()).filter(timestamp_col >= start).group_by(date_col)
    if extra_filters:
        q = q.filter(*extra_filters)
    rows = {str(r[0]): r[1] for r in q.all()}
    result = []
    for i in range(days - 1, -1, -1):
        d = (now - timedelta(days=i)).strftime("%m-%d")
        db_date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        result.append((d, rows.get(db_date, 0)))
    return result


class AdminDashboardResource(Resource):
    """
    Admin Dashboard Statistics
    ---
    tags: [Dashboard]
    security: [Bearer: []]
    responses:
      200: {description: Dashboard data}
      403: {description: Not authorized}
    """

    @jwt_required()
    @admin_required
    @relaxed_limit
    @cached(timeout=120, key_prefix="dashboard")
    def get(self):
        identity = get_jwt_identity()
        if not is_admin_role(identity.get("role")):
            return {"status": False, "msg": "无权访问"}, 403

        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # ========== 基础统计（6 条查询） ==========
        total_users = EmployeeAccount.query.count()
        total_admins = AdmAccount.query.count()
        pending_applications = Application.query.filter(Application.adm1_statu == None).count()
        total_applications = Application.query.count()

        try:
            vector_count = Shp.query.count()
            raster_count = RasterData.query.count()
        except Exception as e:
            logging.error(f"PostgreSQL查询失败: {e}")
            vector_count = 0
            raster_count = 0

        total_downloads = DownloadRecord.query.count()

        # ========== 今日统计（1 条聚合查询替代 4 条） ==========
        today_counts = dict(
            db.session.query(LogInfo.action, func.count(func.distinct(LogInfo.user_number)))
            .filter(LogInfo.timestamp >= today_start, LogInfo.action.in_(["login", "download", "apply", "view"]))
            .group_by(LogInfo.action)
            .all()
        )
        active_users_today = sum(today_counts.values())
        logins_today = today_counts.get("login", 0)

        today_apps_downloads = dict(
            db.session.query(
                case((Application.application_submission_time >= today_start, "apps"), else_="other"),
                func.count(),
            )
            .group_by(case((Application.application_submission_time >= today_start, "apps"), else_="other"))
            .all()
        )
        applications_today = today_apps_downloads.get("apps", 0)

        today_dl = db.session.query(func.count()).filter(DownloadRecord.timestamp >= today_start).scalar()
        downloads_today = today_dl or 0

        # ========== 14天趋势（3 条批量 GROUP BY 替代 42 条） ==========
        app_trend = _batch_day_counts(Application, Application.application_submission_time, 14)
        dl_trend = _batch_day_counts(DownloadRecord, DownloadRecord.timestamp, 14)
        login_trend = _batch_day_counts(LogInfo, LogInfo.timestamp, 14, [LogInfo.action == "login"])
        daily_trend = [
            {"date": d, "applications": a, "downloads": dl, "logins": lg}
            for (d, a), (_, dl), (_, lg) in zip(app_trend, dl_trend, login_trend)
        ]

        # ========== 本周 vs 上周（4 条查询） ==========
        this_week_start = now - timedelta(days=now.weekday())
        this_week_start = this_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        last_week_start = this_week_start - timedelta(days=7)

        this_week_apps = Application.query.filter(Application.application_submission_time >= this_week_start).count()
        last_week_apps = Application.query.filter(
            Application.application_submission_time >= last_week_start,
            Application.application_submission_time < this_week_start,
        ).count()
        this_week_downloads = DownloadRecord.query.filter(DownloadRecord.timestamp >= this_week_start).count()
        last_week_downloads = DownloadRecord.query.filter(
            DownloadRecord.timestamp >= last_week_start, DownloadRecord.timestamp < this_week_start
        ).count()

        app_growth = ((this_week_apps - last_week_apps) / last_week_apps * 100) if last_week_apps > 0 else 0
        download_growth = (
            ((this_week_downloads - last_week_downloads) / last_week_downloads * 100) if last_week_downloads > 0 else 0
        )

        # ========== 状态分布（1 条聚合替代 3 条） ==========
        status_rows = dict(
            db.session.query(
                case(
                    (and_(Application.adm1_statu == True, Application.adm2_statu == True), "approved"),
                    (or_(Application.adm1_statu == False, Application.adm2_statu == False), "rejected"),
                    else_="pending",
                ),
                func.count(),
            )
            .group_by(
                case(
                    (and_(Application.adm1_statu == True, Application.adm2_statu == True), "approved"),
                    (or_(Application.adm1_statu == False, Application.adm2_statu == False), "rejected"),
                    else_="pending",
                )
            )
            .all()
        )
        status_distribution = {
            "pending": status_rows.get("pending", 0),
            "approved": status_rows.get("approved", 0),
            "rejected": status_rows.get("rejected", 0),
        }

        # ========== 热门数据 TOP 5（有下载的优先，不足则补最近审批通过的数据） ==========
        hot_data = (
            db.session.query(
                Application.data_name, Application.data_type, func.count(DownloadRecord.id).label("download_count")
            )
            .outerjoin(DownloadRecord, DownloadRecord.application_id == Application.id)
            .group_by(Application.data_name, Application.data_type)
            .order_by(func.count(DownloadRecord.id).desc())
            .limit(5)
            .all()
        )
        hot_data_list = [
            {"name": row[0] or "未知数据", "type": (row[1] or "unknown").lower(), "downloads": row[2]}
            for row in hot_data
        ]
        # 不足 5 条时，用最近审批通过的数据补齐
        if len(hot_data_list) < 5:
            existing_names = {row["name"] for row in hot_data_list}
            extra = (
                Application.query.with_entities(Application.data_name, Application.data_type)
                .filter(Application.adm1_statu == True, Application.adm2_statu == True)
                .filter(~Application.data_name.in_(existing_names))
                .order_by(Application.application_submission_time.desc())
                .limit(5 - len(hot_data_list))
                .all()
            )
            for row in extra:
                hot_data_list.append(
                    {
                        "name": row.data_name or "未知数据",
                        "type": (row.data_type or "unknown").lower(),
                        "downloads": 0,
                    }
                )

        # ========== 管理员效率（批量查询替代 N×3 循环） ==========
        admin_stats = []
        admins_with_info = (
            db.session.query(AdmAccount, AdmInfo.name)
            .outerjoin(AdmInfo, AdmAccount.adm_number == AdmInfo.adm_number)
            .all()
        )
        if admins_with_info:
            admin_numbers = [a.adm_number for a, _ in admins_with_info]
            # 一次查出所有审批统计
            approved_counts = dict(
                db.session.query(Application.adm1_user_number, func.count())
                .filter(
                    Application.adm1_user_number.in_(admin_numbers),
                    Application.adm1_statu == True,
                    Application.adm2_statu == True,
                )
                .group_by(Application.adm1_user_number)
                .all()
            )
            approved_counts2 = dict(
                db.session.query(Application.adm2_user_number, func.count())
                .filter(
                    Application.adm2_user_number.in_(admin_numbers),
                    Application.adm1_statu == True,
                    Application.adm2_statu == True,
                )
                .group_by(Application.adm2_user_number)
                .all()
            )
            rejected_counts = dict(
                db.session.query(Application.adm1_user_number, func.count())
                .filter(
                    Application.adm1_user_number.in_(admin_numbers),
                    Application.adm1_statu == False,
                )
                .group_by(Application.adm1_user_number)
                .all()
            )
            rejected_counts2 = dict(
                db.session.query(Application.adm2_user_number, func.count())
                .filter(
                    Application.adm2_user_number.in_(admin_numbers),
                    Application.adm2_statu == False,
                )
                .group_by(Application.adm2_user_number)
                .all()
            )
            for admin, name in admins_with_info:
                num = admin.adm_number
                ap = approved_counts.get(num, 0) + approved_counts2.get(num, 0)
                rj = rejected_counts.get(num, 0) + rejected_counts2.get(num, 0)
                admin_stats.append(
                    {
                        "name": name or admin.adm_user_name,
                        "number": num,
                        "approved": ap,
                        "rejected": rj,
                        "total": ap + rj,
                    }
                )

        # ========== 每小时活跃度（1 条 GROUP BY 替代 24 条） ==========
        hourly_rows = dict(
            db.session.query(func.extract("hour", LogInfo.timestamp), func.count())
            .filter(
                LogInfo.timestamp >= today_start,
                LogInfo.action.in_(["login", "download", "apply"]),
            )
            .group_by(func.extract("hour", LogInfo.timestamp))
            .all()
        )
        hourly_activity = [{"hour": f"{h:02d}:00", "count": hourly_rows.get(h, 0)} for h in range(24)]

        # ========== 回收审议 + 管理员申请（各自 1 条聚合） ==========
        recall_rows = dict(db.session.query(RecallProposal.status, func.count()).group_by(RecallProposal.status).all())
        recall_stats = {
            "voting": recall_rows.get("voting", 0),
            "approved": recall_rows.get("approved", 0),
            "rejected": recall_rows.get("rejected", 0),
            "recalled_data": Application.query.filter_by(is_recalled=True).count(),
        }

        admin_app_rows = dict(
            db.session.query(AdminApplication.status, func.count()).group_by(AdminApplication.status).all()
        )
        admin_app_stats = {
            "pending": admin_app_rows.get("pending", 0),
            "voting": admin_app_rows.get("voting", 0),
            "approved": admin_app_rows.get("approved", 0),
            "rejected": admin_app_rows.get("rejected", 0),
        }

        # ========== 告警 ==========
        alerts = []
        if pending_applications > 20:
            alerts.append(
                {
                    "level": "warning",
                    "type": "pending_overflow",
                    "message": f"待审批申请积压达 {pending_applications} 条，请及时处理",
                    "count": pending_applications,
                }
            )
        if active_users_today == 0:
            alerts.append({"level": "info", "type": "no_activity", "message": "今日尚无用户活动记录"})
        if recall_stats["voting"] > 0:
            alerts.append(
                {
                    "level": "warning",
                    "type": "recall_pending",
                    "message": f"有 {recall_stats['voting']} 条数据回收提议待投票",
                    "count": recall_stats["voting"],
                }
            )
        if admin_app_stats["pending"] > 0 or admin_app_stats["voting"] > 0:
            alerts.append(
                {
                    "level": "info",
                    "type": "admin_app_pending",
                    "message": f"有 {admin_app_stats['pending'] + admin_app_stats['voting']} 条管理员申请待处理",
                }
            )

        # ========== 最近日志（1 条查询） ==========
        recent_logs = [
            {"action": log.action, "username": log.username, "timestamp": log.timestamp.isoformat()}
            for log in LogInfo.query.order_by(LogInfo.timestamp.desc()).limit(10).all()
        ]

        return {
            "status": True,
            "data": {
                "total_users": total_users,
                "total_admins": total_admins,
                "pending_applications": pending_applications,
                "total_applications": total_applications,
                "total_datasets": vector_count + raster_count,
                "total_downloads": total_downloads,
                "today": {
                    "active_users": active_users_today,
                    "logins": logins_today,
                    "applications": applications_today,
                    "downloads": downloads_today,
                },
                "weekly_comparison": {
                    "this_week_applications": this_week_apps,
                    "last_week_applications": last_week_apps,
                    "application_growth": round(app_growth, 1),
                    "this_week_downloads": this_week_downloads,
                    "last_week_downloads": last_week_downloads,
                    "download_growth": round(download_growth, 1),
                },
                "admin_efficiency": admin_stats,
                "hot_data": hot_data_list,
                "hourly_activity": hourly_activity,
                "recall_stats": recall_stats,
                "admin_application_stats": admin_app_stats,
                "alerts": alerts,
                "daily_trend": daily_trend,
                "status_distribution": status_distribution,
                "data_type_stats": {"vector": vector_count, "raster": raster_count},
                "recent_logs": recent_logs,
            },
        }, 200


class EmployeeDashboardResource(Resource):
    @jwt_required()
    def get(self):
        identity = get_jwt_identity()
        user_number = identity.get("number") or request.args.get("userNumber")
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # ========== 基础统计（4 条查询） ==========
        total_apps = Application.query.filter_by(applicant_user_number=user_number).count()
        pending_apps = Application.query.filter_by(applicant_user_number=user_number, adm1_statu=None).count()
        downloadable = Application.query.filter_by(
            applicant_user_number=user_number, adm1_statu=True, adm2_statu=True
        ).count()
        my_downloads = DownloadRecord.query.filter_by(applicant_user_number=user_number).count()

        # 今日活跃 + 最近登录（1 条聚合 + 1 条查询）
        today_visits = LogInfo.query.filter(
            LogInfo.user_number == user_number, LogInfo.action == "login", LogInfo.timestamp >= today_start
        ).count()

        last_login = (
            LogInfo.query.filter(LogInfo.user_number == user_number, LogInfo.action == "login")
            .order_by(LogInfo.timestamp.desc())
            .first()
        )

        # 数据偏好（1 条聚合替代 2 条）
        pref_rows = dict(
            db.session.query(func.lower(Application.data_type), func.count())
            .filter(Application.applicant_user_number == user_number)
            .group_by(func.lower(Application.data_type))
            .all()
        )
        vector_prefs = pref_rows.get("vector", 0)
        raster_prefs = pref_rows.get("raster", 0)

        # 最近申请（1 条查询）
        recent_apps = (
            Application.query.filter_by(applicant_user_number=user_number)
            .order_by(Application.application_submission_time.desc())
            .limit(5)
            .all()
        )
        recent_applications = [
            {
                "id": app.id,
                "data_name": app.data_name,
                "data_type": app.data_type,
                "status": "已通过"
                if (app.adm1_statu and app.adm2_statu)
                else ("已拒绝" if (app.adm1_statu == False or app.adm2_statu == False) else "待审批"),
                "submission_time": app.application_submission_time.strftime("%Y-%m-%d %H:%M")
                if app.application_submission_time
                else "-",
            }
            for app in recent_apps
        ]

        # ========== 14天趋势（2 条批量 GROUP BY 替代 28 条） ==========
        app_trend = _batch_day_counts(
            Application,
            Application.application_submission_time,
            14,
            [Application.applicant_user_number == user_number],
        )
        dl_trend = _batch_day_counts(
            DownloadRecord,
            DownloadRecord.timestamp,
            14,
            [DownloadRecord.applicant_user_number == user_number],
        )
        daily_trend = [{"date": d, "applications": a, "downloads": dl} for (d, a), (_, dl) in zip(app_trend, dl_trend)]

        # 状态分布（1 条聚合替代 3 条）
        status_rows = dict(
            db.session.query(
                case(
                    (and_(Application.adm1_statu == True, Application.adm2_statu == True), "approved"),
                    (or_(Application.adm1_statu == False, Application.adm2_statu == False), "rejected"),
                    else_="pending",
                ),
                func.count(),
            )
            .filter(Application.applicant_user_number == user_number)
            .group_by(
                case(
                    (and_(Application.adm1_statu == True, Application.adm2_statu == True), "approved"),
                    (or_(Application.adm1_statu == False, Application.adm2_statu == False), "rejected"),
                    else_="pending",
                )
            )
            .all()
        )
        status_dist = {
            "pending": status_rows.get("pending", 0),
            "approved": status_rows.get("approved", 0),
            "rejected": status_rows.get("rejected", 0),
        }

        return {
            "status": True,
            "data": {
                "total_applications": total_apps,
                "pending_applications": pending_apps,
                "downloadable_data": downloadable,
                "my_downloads": my_downloads,
                "today_visits": today_visits or 1,
                "last_login_time": last_login.timestamp.strftime("%Y-%m-%d %H:%M")
                if last_login
                else now.strftime("%Y-%m-%d %H:%M"),
                "data_type_preference": {"vector": vector_prefs, "raster": raster_prefs},
                "recent_applications": recent_applications,
                "daily_trend": daily_trend,
                "application_status_distribution": status_dist,
            },
        }, 200
