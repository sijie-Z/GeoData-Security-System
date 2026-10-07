import csv
import io
import logging
from datetime import UTC, datetime, timedelta

from flask import Response, request
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
from model.Employee_Info import EmployeeInfo
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


#: Allowed values of the ``days`` query parameter for the download-stats board
#: (the UI offers 7/30/90; 14 is accepted for API symmetry with dl_trend).
DOWNLOAD_STATS_ALLOWED_DAYS = (7, 14, 30, 90)
DOWNLOAD_STATS_DEFAULT_DAYS = 30
DOWNLOAD_STATS_TOP_LIMIT = 10


def _clamped_days():
    """``days`` constrained to {7,14,30,90}; anything else (missing, non-integer,
    out of set) falls back to 30."""
    days = request.args.get("days", default=DOWNLOAD_STATS_DEFAULT_DAYS, type=int)
    return days if days in DOWNLOAD_STATS_ALLOWED_DAYS else DOWNLOAD_STATS_DEFAULT_DAYS


def _collect_download_stats(days):
    """Download statistics over the last ``days`` days — pure SQL aggregates.

    * ``daily``      per-day download count + distinct downloaders (one GROUP BY
                     with a fill-in loop, same shape as ``_batch_day_counts``)
    * ``top_users``  top downloaders inside the window, display names resolved
                     with ONE batched ``IN`` lookup (no N+1)
    * ``top_data``   top applications inside the window (data_name/data_type),
                     types resolved with ONE batched ``IN`` lookup
    * ``comparison`` fixed 7-days-vs-previous-7-days counts and growth
    """
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    window_start = today_start - timedelta(days=days - 1)

    date_col = func.date(DownloadRecord.timestamp)
    daily_rows = {
        str(row[0]): (row[1], row[2])
        for row in db.session.query(
            date_col,
            func.count(),
            func.count(func.distinct(DownloadRecord.download_user_number)),
        )
        .filter(DownloadRecord.timestamp >= window_start)
        .group_by(date_col)
        .all()
    }
    daily = []
    for i in range(days - 1, -1, -1):
        day = now - timedelta(days=i)
        downloads, users = daily_rows.get(day.strftime("%Y-%m-%d"), (0, 0))
        daily.append({"date": day.strftime("%m-%d"), "downloads": int(downloads), "users": int(users)})

    top_user_rows = (
        db.session.query(DownloadRecord.download_user_number, func.count().label("downloads"))
        .filter(DownloadRecord.timestamp >= window_start)
        .group_by(DownloadRecord.download_user_number)
        .order_by(func.count().desc(), DownloadRecord.download_user_number.asc())
        .limit(DOWNLOAD_STATS_TOP_LIMIT)
        .all()
    )
    user_numbers = [row[0] for row in top_user_rows if row[0]]
    user_names = {}
    if user_numbers:
        user_names = dict(
            db.session.query(EmployeeInfo.employee_number, EmployeeInfo.name)
            .filter(EmployeeInfo.employee_number.in_(user_numbers))
            .all()
        )
    top_users = [
        {"user_number": row[0] or "", "name": user_names.get(row[0]), "downloads": int(row[1])} for row in top_user_rows
    ]

    top_data_rows = (
        db.session.query(DownloadRecord.application_id, DownloadRecord.data_name, func.count().label("downloads"))
        .filter(DownloadRecord.timestamp >= window_start)
        .group_by(DownloadRecord.application_id, DownloadRecord.data_name)
        .order_by(func.count().desc(), DownloadRecord.application_id.asc())
        .limit(DOWNLOAD_STATS_TOP_LIMIT)
        .all()
    )
    app_ids = [row[0] for row in top_data_rows if row[0]]
    app_types = {}
    if app_ids:
        app_types = dict(
            db.session.query(Application.id, Application.data_type).filter(Application.id.in_(app_ids)).all()
        )
    top_data = [
        {
            "application_id": row[0],
            "data_name": row[1] or "",
            "data_type": (app_types.get(row[0]) or "unknown").lower() if row[0] else "unknown",
            "downloads": int(row[2]),
        }
        for row in top_data_rows
    ]

    this_week_start = now - timedelta(days=7)
    last_week_start = now - timedelta(days=14)
    week_cols = (func.count(), func.count(func.distinct(DownloadRecord.download_user_number)))
    this_week = db.session.query(*week_cols).filter(DownloadRecord.timestamp >= this_week_start).first()
    last_week = (
        db.session.query(*week_cols)
        .filter(DownloadRecord.timestamp >= last_week_start, DownloadRecord.timestamp < this_week_start)
        .first()
    )
    this_dl, this_users = int(this_week[0]), int(this_week[1])
    last_dl, last_users = int(last_week[0]), int(last_week[1])

    def _growth(current, previous):
        return round((current - previous) / previous * 100, 1) if previous else 0

    comparison = {
        "this_week_downloads": this_dl,
        "last_week_downloads": last_dl,
        "downloads_growth": _growth(this_dl, last_dl),
        "this_week_users": this_users,
        "last_week_users": last_users,
        "users_growth": _growth(this_users, last_users),
    }

    return {"days": days, "daily": daily, "top_users": top_users, "top_data": top_data, "comparison": comparison}


def _download_stats_csv(days, stats, generated_at):
    """Multi-section CSV: metadata row, then [每日下载] / [Top 用户] / [Top 数据]
    / [近7天 vs 前7天] blocks in one file (documented export format)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["下载统计导出", f"窗口=近{days}天", f"生成时间={generated_at} (UTC)"])
    writer.writerow([])

    writer.writerow(["[每日下载]"])
    writer.writerow(["日期", "下载量", "独立下载人数"])
    for row in stats["daily"]:
        writer.writerow([row["date"], row["downloads"], row["users"]])
    writer.writerow([])

    writer.writerow(["[Top 用户]"])
    writer.writerow(["排名", "用户编号", "姓名", "下载次数"])
    for idx, row in enumerate(stats["top_users"], start=1):
        writer.writerow([idx, row["user_number"], row["name"] or "", row["downloads"]])
    writer.writerow([])

    writer.writerow(["[Top 数据]"])
    writer.writerow(["排名", "申请ID", "数据名称", "数据类型", "下载次数"])
    for idx, row in enumerate(stats["top_data"], start=1):
        app_id = row["application_id"] if row["application_id"] is not None else ""
        writer.writerow([idx, app_id, row["data_name"], row["data_type"], row["downloads"]])
    writer.writerow([])

    comparison = stats["comparison"]
    writer.writerow(["[近7天 vs 前7天]"])
    writer.writerow(["指标", "近7天", "前7天", "增长率%"])
    writer.writerow(
        ["下载量", comparison["this_week_downloads"], comparison["last_week_downloads"], comparison["downloads_growth"]]
    )
    writer.writerow(
        [
            "独立下载人数",
            comparison["this_week_users"],
            comparison["last_week_users"],
            comparison["users_growth"],
        ]
    )
    return buffer.getvalue()


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


class AdminDownloadStatsResource(Resource):
    """GET /api/admin/download_stats?days=30 — admin. Download-stats board data:
    daily downloads + unique downloaders, Top users, Top data and the fixed
    7-days-vs-previous-7-days comparison. All aggregates are single SQL queries.
    """

    @admin_required
    def get(self):
        days = _clamped_days()
        return {"status": True, "data": _collect_download_stats(days)}, 200


class AdminDownloadStatsExportResource(Resource):
    """GET /api/admin/download_stats/export?days= — admin. Multi-section CSV of
    the same data (BOM, csv-module escaping): [每日下载] / [Top 用户] /
    [Top 数据] / [近7天 vs 前7天] blocks in one file.
    """

    @admin_required
    def get(self):
        days = _clamped_days()
        stats = _collect_download_stats(days)
        generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        payload = ("\ufeff" + _download_stats_csv(days, stats, generated_at)).encode("utf-8")
        filename = f"download_stats_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.csv"
        response = Response(payload, mimetype="text/csv")
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        return response


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
