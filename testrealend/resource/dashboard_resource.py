from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from model.Employee_Account import EmployeeAccount
from model.Adm_Account import AdmAccount
from model.Adm_Info import AdmInfo
from model.Application import Application
from model.Shp_Data import Shp
from model.Raster_Data import RasterData
from model.Download_Record import DownloadRecord
from model.Log_Info import LogInfo
from model.RecallProposal import RecallProposal
from model.AdminApplication import AdminApplication
from extension.extension import db
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
import calendar
import logging
from utils.cache import cached


def _day_window(days_ago):
    end = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1 - days_ago)
    start = end - timedelta(days=1)
    return start, end


def _get_hour_of_day(dt):
    """Get hour bucket for hourly analysis"""
    return dt.hour


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
    @cached(timeout=120, key_prefix='dashboard')
    def get(self):
        identity = get_jwt_identity()
        if identity.get('role') != 'admin':
            return {'status': False, 'msg': '无权访问'}, 403

        # ========== 基础统计 ==========
        total_users = EmployeeAccount.query.count()
        total_admins = AdmAccount.query.count()
        pending_applications = Application.query.filter(Application.adm1_statu == None).count()
        total_applications = Application.query.count()

        # 数据资产统计 - 使用ORM直接查询PostgreSQL
        try:
            vector_count = Shp.query.count()
            raster_count = RasterData.query.count()
        except Exception as e:
            logging.error(f'PostgreSQL查询失败: {e}')
            vector_count = 0
            raster_count = 0
        total_datasets = vector_count + raster_count

        # 下载统计
        total_downloads = DownloadRecord.query.count()

        # ========== 今日活跃用户 ==========
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        active_users_today = db.session.query(func.count(func.distinct(LogInfo.user_number))).filter(
            LogInfo.timestamp >= today_start,
            LogInfo.action.in_(['login', 'download', 'apply', 'view'])
        ).scalar() or 0

        # 今日登录数
        logins_today = LogInfo.query.filter(
            LogInfo.action == 'login',
            LogInfo.timestamp >= today_start
        ).count()

        # 今日申请数
        applications_today = Application.query.filter(
            Application.application_submission_time >= today_start
        ).count()

        # 今日下载数
        downloads_today = DownloadRecord.query.filter(
            DownloadRecord.timestamp >= today_start
        ).count()

        # ========== 管理员效率统计 ==========
        admin_stats = []
        admins = AdmAccount.query.all()

        for admin in admins:
            # 统计每个管理员的审批数
            approved_count = Application.query.filter(
                or_(
                    Application.adm1_user_number == admin.adm_number,
                    Application.adm2_user_number == admin.adm_number
                ),
                Application.adm1_statu == True,
                Application.adm2_statu == True
            ).count()

            rejected_count = Application.query.filter(
                or_(
                    and_(Application.adm1_user_number == admin.adm_number, Application.adm1_statu == False),
                    and_(Application.adm2_user_number == admin.adm_number, Application.adm2_statu == False)
                )
            ).count()

            # 获取管理员姓名
            admin_info = db.session.query(AdmInfo).filter_by(adm_number=admin.adm_number).first()
            admin_name = admin_info.name if admin_info else admin.adm_user_name

            admin_stats.append({
                'name': admin_name,
                'number': admin.adm_number,
                'approved': approved_count,
                'rejected': rejected_count,
                'total': approved_count + rejected_count
            })

        # ========== 热门数据TOP10 ==========
        # 基于下载次数统计
        hot_data = db.session.query(
            Application.data_name,
            Application.data_type,
            func.count(DownloadRecord.id).label('download_count')
        ).join(
            DownloadRecord,
            DownloadRecord.application_id == Application.id
        ).group_by(Application.data_name, Application.data_type).order_by(
            func.count(DownloadRecord.id).desc()
        ).limit(10).all()

        hot_data_list = [{
            'name': row[0] or '未知数据',
            'type': row[1] or 'unknown',
            'downloads': row[2]
        } for row in hot_data]

        # ========== 申请类型分布 ==========
        type_distribution = db.session.query(
            Application.data_type,
            func.count(Application.id).label('count')
        ).group_by(Application.data_type).all()

        type_dist = {row[0] or 'unknown': row[1] for row in type_distribution}

        # ========== 每小时活跃度（今日） ==========
        hourly_activity = []
        for hour in range(24):
            hour_start = today_start + timedelta(hours=hour)
            hour_end = hour_start + timedelta(hours=1)

            activity_count = LogInfo.query.filter(
                LogInfo.timestamp >= hour_start,
                LogInfo.timestamp < hour_end,
                LogInfo.action.in_(['login', 'download', 'apply'])
            ).count()

            hourly_activity.append({
                'hour': f'{hour:02d}:00',
                'count': activity_count
            })

        # ========== 本周 vs 上周对比 ==========
        this_week_start = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
        this_week_start = this_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        last_week_start = this_week_start - timedelta(days=7)
        last_week_end = this_week_start

        this_week_apps = Application.query.filter(
            Application.application_submission_time >= this_week_start
        ).count()

        last_week_apps = Application.query.filter(
            Application.application_submission_time >= last_week_start,
            Application.application_submission_time < last_week_end
        ).count()

        this_week_downloads = DownloadRecord.query.filter(
            DownloadRecord.timestamp >= this_week_start
        ).count()

        last_week_downloads = DownloadRecord.query.filter(
            DownloadRecord.timestamp >= last_week_start,
            DownloadRecord.timestamp < last_week_end
        ).count()

        # 计算增长率
        app_growth = ((this_week_apps - last_week_apps) / last_week_apps * 100) if last_week_apps > 0 else 0
        download_growth = ((this_week_downloads - last_week_downloads) / last_week_downloads * 100) if last_week_downloads > 0 else 0

        # ========== 回收审议统计 ==========
        recall_stats = {
            'voting': RecallProposal.query.filter_by(status='voting').count(),
            'approved': RecallProposal.query.filter_by(status='approved').count(),
            'rejected': RecallProposal.query.filter_by(status='rejected').count(),
            'recalled_data': Application.query.filter_by(is_recalled=True).count()
        }

        # ========== 管理员申请统计 ==========
        admin_app_stats = {
            'pending': AdminApplication.query.filter_by(status='pending').count(),
            'voting': AdminApplication.query.filter_by(status='voting').count(),
            'approved': AdminApplication.query.filter_by(status='approved').count(),
            'rejected': AdminApplication.query.filter_by(status='rejected').count()
        }

        # ========== 异常告警 ==========
        alerts = []

        # 待审批过多告警
        if pending_applications > 20:
            alerts.append({
                'level': 'warning',
                'type': 'pending_overflow',
                'message': f'待审批申请积压达 {pending_applications} 条，请及时处理',
                'count': pending_applications
            })

        # 今日无活跃告警
        if active_users_today == 0:
            alerts.append({
                'level': 'info',
                'type': 'no_activity',
                'message': '今日尚无用户活动记录'
            })

        # 回收审议待处理
        if recall_stats['voting'] > 0:
            alerts.append({
                'level': 'warning',
                'type': 'recall_pending',
                'message': f'有 {recall_stats["voting"]} 条数据回收提议待投票',
                'count': recall_stats['voting']
            })

        # 管理员申请待处理
        if admin_app_stats['pending'] > 0 or admin_app_stats['voting'] > 0:
            alerts.append({
                'level': 'info',
                'type': 'admin_app_pending',
                'message': f'有 {admin_app_stats["pending"] + admin_app_stats["voting"]} 条管理员申请待处理'
            })

        # ========== 14天趋势数据 ==========
        daily_trend = []
        for i in range(13, -1, -1):
            date = (datetime.utcnow() - timedelta(days=i)).strftime('%m-%d')
            start, end = _day_window(i)

            app_count = Application.query.filter(
                Application.application_submission_time >= start,
                Application.application_submission_time < end
            ).count()

            dl_count = DownloadRecord.query.filter(
                DownloadRecord.timestamp >= start,
                DownloadRecord.timestamp < end
            ).count()

            login_count = LogInfo.query.filter(
                LogInfo.action == 'login',
                LogInfo.timestamp >= start,
                LogInfo.timestamp < end
            ).count()

            daily_trend.append({
                'date': date,
                'applications': app_count,
                'downloads': dl_count,
                'logins': login_count
            })

        # ========== 状态分布 ==========
        status_distribution = {
            'pending': pending_applications,
            'approved': Application.query.filter(Application.adm1_statu == True, Application.adm2_statu == True).count(),
            'rejected': Application.query.filter(
                or_(Application.adm1_statu == False, Application.adm2_statu == False)
            ).count()
        }

        # ========== 最近日志 ==========
        recent_logs = []
        logs = LogInfo.query.order_by(LogInfo.timestamp.desc()).limit(10).all()
        for log in logs:
            recent_logs.append({
                'action': log.action,
                'username': log.username,
                'timestamp': log.timestamp.isoformat()
            })

        # ========== 月度统计（最近6个月） ==========
        monthly_stats = []
        for i in range(5, -1, -1):
            month_date = datetime.utcnow() - timedelta(days=i*30)
            month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if i > 0:
                month_end = (datetime.utcnow() - timedelta(days=(i-1)*30)).replace(day=1)
            else:
                month_end = datetime.utcnow() + timedelta(days=1)

            month_apps = Application.query.filter(
                Application.application_submission_time >= month_start,
                Application.application_submission_time < month_end
            ).count()

            month_downloads = DownloadRecord.query.filter(
                DownloadRecord.timestamp >= month_start,
                DownloadRecord.timestamp < month_end
            ).count()

            monthly_stats.append({
                'month': month_start.strftime('%Y-%m'),
                'applications': month_apps,
                'downloads': month_downloads
            })

        return {
            'status': True,
            'data': {
                # 基础统计
                'total_users': total_users,
                'total_admins': total_admins,
                'pending_applications': pending_applications,
                'total_applications': total_applications,
                'total_datasets': total_datasets,
                'total_downloads': total_downloads,

                # 今日数据
                'today': {
                    'active_users': active_users_today,
                    'logins': logins_today,
                    'applications': applications_today,
                    'downloads': downloads_today
                },

                # 周对比
                'weekly_comparison': {
                    'this_week_applications': this_week_apps,
                    'last_week_applications': last_week_apps,
                    'application_growth': round(app_growth, 1),
                    'this_week_downloads': this_week_downloads,
                    'last_week_downloads': last_week_downloads,
                    'download_growth': round(download_growth, 1)
                },

                # 管理员效率
                'admin_efficiency': admin_stats,

                # 热门数据
                'hot_data': hot_data_list,

                # 类型分布
                'type_distribution': type_dist,

                # 每小时活跃度
                'hourly_activity': hourly_activity,

                # 月度统计
                'monthly_stats': monthly_stats,

                # 回收审议
                'recall_stats': recall_stats,

                # 管理员申请
                'admin_application_stats': admin_app_stats,

                # 告警信息
                'alerts': alerts,

                # 14天趋势
                'daily_trend': daily_trend,

                # 状态分布
                'status_distribution': status_distribution,

                # 数据类型统计
                'data_type_stats': {
                    'vector': vector_count,
                    'raster': raster_count
                },

                # 最近日志
                'recent_logs': recent_logs
            }
        }, 200


class EmployeeDashboardResource(Resource):
    @jwt_required()
    def get(self):
        identity = get_jwt_identity()
        user_number = identity.get('number') or request.args.get('userNumber')

        # 基础统计
        total_apps = Application.query.filter_by(applicant_user_number=user_number).count()
        pending_apps = Application.query.filter_by(applicant_user_number=user_number, adm1_statu=None).count()
        downloadable = Application.query.filter_by(applicant_user_number=user_number, adm1_statu=True, adm2_statu=True).count()
        my_downloads = DownloadRecord.query.filter_by(applicant_user_number=user_number).count()

        # 今日活跃
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_visits = LogInfo.query.filter(
            LogInfo.user_number == user_number,
            LogInfo.action == 'login',
            LogInfo.timestamp >= today_start
        ).count()

        last_login = LogInfo.query.filter(
            LogInfo.user_number == user_number,
            LogInfo.action == 'login'
        ).order_by(LogInfo.timestamp.desc()).first()

        # 我的数据偏好
        vector_prefs = Application.query.filter_by(applicant_user_number=user_number).filter(
            db.func.lower(Application.data_type) == 'vector'
        ).count()
        raster_prefs = Application.query.filter_by(applicant_user_number=user_number).filter(
            db.func.lower(Application.data_type) == 'raster'
        ).count()

        # 最近申请
        recent_apps = Application.query.filter_by(applicant_user_number=user_number).order_by(
            Application.application_submission_time.desc()
        ).limit(5).all()

        recent_applications = [{
            'id': app.id,
            'data_name': app.data_name,
            'data_type': app.data_type,
            'status': '已通过' if (app.adm1_statu and app.adm2_statu) else ('已拒绝' if (app.adm1_statu == False or app.adm2_statu == False) else '待审批'),
            'submission_time': app.application_submission_time.strftime('%Y-%m-%d %H:%M') if app.application_submission_time else '-'
        } for app in recent_apps]

        # 14天趋势
        daily_trend = []
        for i in range(13, -1, -1):
            date = (datetime.utcnow() - timedelta(days=i)).strftime('%m-%d')
            start, end = _day_window(i)

            app_count = Application.query.filter(
                Application.applicant_user_number == user_number,
                Application.application_submission_time >= start,
                Application.application_submission_time < end
            ).count()

            dl_count = DownloadRecord.query.filter(
                DownloadRecord.applicant_user_number == user_number,
                DownloadRecord.timestamp >= start,
                DownloadRecord.timestamp < end
            ).count()

            daily_trend.append({
                'date': date,
                'applications': app_count,
                'downloads': dl_count
            })

        # 申请状态分布
        status_dist = {
            'pending': pending_apps,
            'approved': downloadable,
            'rejected': Application.query.filter_by(applicant_user_number=user_number).filter(
                or_(Application.adm1_statu == False, Application.adm2_statu == False)
            ).count()
        }

        return {
            'status': True,
            'data': {
                'total_applications': total_apps,
                'pending_applications': pending_apps,
                'downloadable_data': downloadable,
                'my_downloads': my_downloads,
                'today_visits': today_visits or 1,
                'last_login_time': last_login.timestamp.strftime('%Y-%m-%d %H:%M') if last_login else datetime.utcnow().strftime('%Y-%m-%d %H:%M'),
                'data_type_preference': {
                    'vector': vector_prefs,
                    'raster': raster_prefs
                },
                'recent_applications': recent_applications,
                'daily_trend': daily_trend,
                'application_status_distribution': status_dist
            }
        }, 200
