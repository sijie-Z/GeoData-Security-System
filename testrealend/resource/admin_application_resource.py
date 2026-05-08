from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import logging
import json

from extension.extension import db
from utils.required import is_admin_role
from model.AdminApplication import AdminApplication
from model.Employee_Info import EmployeeInfo
from model.Employee_Account import EmployeeAccount
from model.Adm_Account import AdmAccount
from model.Adm_Info import AdmInfo


class AdminApplicationEligibilityResource(Resource):
    """检查员工是否有资格申请成为管理员"""
    @jwt_required()
    def get(self):
        identity = get_jwt_identity()
        user_number = identity.get('number')
        role = identity.get('role')

        # Already an admin
        if is_admin_role(role):
            return {
                'status': True,
                'data': {
                    'eligible': False,
                    'reason': '您已经是管理员'
                }
            }, 200

        # Get employee info
        emp = EmployeeInfo.query.filter_by(employee_number=user_number).first()
        if not emp:
            return {
                'status': True,
                'data': {
                    'eligible': False,
                    'reason': '员工信息不存在'
                }
            }, 200

        # Check registration time (7+ days)
        if not emp.create_time:
            return {
                'status': True,
                'data': {
                    'eligible': False,
                    'reason': '无法确定注册时间'
                }
            }, 200

        days_registered = (datetime.utcnow() - emp.create_time).days
        if days_registered < 7:
            return {
                'status': True,
                'data': {
                    'eligible': False,
                    'reason': f'注册时间不足7天(当前{days_registered}天)',
                    'days_registered': days_registered,
                    'days_needed': 7 - days_registered
                }
            }, 200

        # Check if there's already a pending application
        from sqlalchemy import or_
        pending = AdminApplication.query.filter_by(
            employee_number=user_number
        ).filter(AdminApplication.status.in_(['pending', 'voting'])).first()

        if pending:
            return {
                'status': True,
                'data': {
                    'eligible': False,
                    'reason': '您已有待处理的申请',
                    'pending_application': pending.to_dict()
                }
            }, 200

        return {
            'status': True,
            'data': {
                'eligible': True,
                'reason': '符合申请条件',
                'days_registered': days_registered
            }
        }, 200


class AdminApplicationSubmitResource(Resource):
    """员工提交管理员申请"""
    @jwt_required()
    def post(self):
        identity = get_jwt_identity()
        user_number = identity.get('number')
        role = identity.get('role')

        if is_admin_role(role):
            return {'status': False, 'msg': '您已经是管理员'}, 400

        data = request.get_json() or {}
        reason = (data.get('reason') or '').strip()

        if len(reason) < 50:
            return {'status': False, 'msg': '申请原因至少需要50个字符'}, 400

        # Get employee info
        emp = EmployeeInfo.query.filter_by(employee_number=user_number).first()
        if not emp:
            return {'status': False, 'msg': '员工信息不存在'}, 404

        # Check registration time
        if emp.create_time:
            days_registered = (datetime.utcnow() - emp.create_time).days
            if days_registered < 7:
                return {'status': False, 'msg': f'注册时间不足7天(当前{days_registered}天)'}, 400

        # Check pending applications
        pending = AdminApplication.query.filter_by(
            employee_number=user_number
        ).filter(AdminApplication.status.in_(['pending', 'voting'])).first()

        if pending:
            return {'status': False, 'msg': '您已有待处理的申请'}, 400

        # Create application
        application = AdminApplication(
            employee_number=user_number,
            employee_name=emp.name,
            reason=reason,
            status='pending'
        )

        try:
            db.session.add(application)
            db.session.commit()

            return {
                'status': True,
                'msg': '申请已提交，等待管理员审核',
                'data': application.to_dict()
            }, 201

        except Exception as e:
            db.session.rollback()
            logging.error(str(e))
            return {'status': False, 'msg': '提交失败，请稍后重试'}, 500


class AdminApplicationMyResource(Resource):
    """获取当前员工的申请状态"""
    @jwt_required()
    def get(self):
        identity = get_jwt_identity()
        user_number = identity.get('number')

        applications = AdminApplication.query.filter_by(
            employee_number=user_number
        ).order_by(AdminApplication.created_at.desc()).all()

        return {
            'status': True,
            'data': [app.to_dict() for app in applications]
        }, 200


class AdminApplicationListResource(Resource):
    """管理员获取所有申请列表"""
    @jwt_required()
    def get(self):
        identity = get_jwt_identity()
        if not is_admin_role(identity.get('role')):
            return {'status': False, 'msg': '只有管理员可以查看'}, 403

        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('pageSize', 10, type=int)
        status_filter = request.args.get('status')

        query = AdminApplication.query.order_by(AdminApplication.created_at.desc())

        if status_filter:
            query = query.filter_by(status=status_filter)

        pagination = query.paginate(page=page, per_page=page_size, error_out=False)

        return {
            'status': True,
            'data': {
                'list': [app.to_dict() for app in pagination.items],
                'total': pagination.total
            }
        }, 200


class AdminApplicationDetailResource(Resource):
    """获取申请详情"""
    @jwt_required()
    def get(self, application_id):
        application = AdminApplication.query.get(application_id)
        if not application:
            return {'status': False, 'msg': '申请不存在'}, 404

        data = application.to_dict()

        # Add employee info
        emp = EmployeeInfo.query.filter_by(employee_number=application.employee_number).first()
        if emp:
            data['employee_info'] = {
                'name': emp.name,
                'phone_number': emp.phone_number,
                'create_time': emp.create_time.strftime('%Y-%m-%d') if emp.create_time else None
            }

        # Add current user's vote status
        identity = get_jwt_identity()
        voter_number = identity.get('number')
        votes = json.loads(application.votes_json) if application.votes_json else {}
        data['my_vote'] = votes.get(voter_number, {}).get('approve', None)
        data['can_vote'] = (
            is_admin_role(identity.get('role')) and
            application.status in ['pending', 'voting']
        )

        return {'status': True, 'data': data}, 200


class AdminApplicationVoteResource(Resource):
    """管理员投票"""
    @jwt_required()
    def post(self, application_id):
        identity = get_jwt_identity()
        voter_number = identity.get('number')

        if not is_admin_role(identity.get('role')):
            return {'status': False, 'msg': '只有管理员可以投票'}, 403

        application = AdminApplication.query.get(application_id)
        if not application:
            return {'status': False, 'msg': '申请不存在'}, 404

        if application.status not in ['pending', 'voting']:
            return {'status': False, 'msg': '该申请已结束审核'}, 400

        data = request.get_json() or {}
        approve = data.get('approve', False)
        comment = (data.get('comment') or '').strip()

        # Update status to voting
        if application.status == 'pending':
            application.status = 'voting'

        # Get voter name
        voter_name = identity.get('username')
        if not voter_name:
            adm_info = AdmInfo.query.filter_by(adm_number=voter_number).first()
            voter_name = adm_info.name if adm_info else voter_number

        application.add_vote(voter_number, voter_name, approve, comment)

        # Check threshold
        total_admins = AdmAccount.query.count()
        result, reason = application.check_threshold(total_admins)

        try:
            if result is True:
                # Approved - convert employee to admin
                application.status = 'approved'
                application.closed_at = datetime.utcnow()
                application.closed_by = voter_number

                # Get employee account
                emp_account = EmployeeAccount.query.filter_by(
                    employee_number=application.employee_number
                ).first()

                if emp_account:
                    # Create admin account
                    adm_account = AdmAccount(
                        adm_user_name=emp_account.employee_user_name,
                        adm_user_password=emp_account.employee_user_password,
                        role='admin',
                        adm_number=application.employee_number
                    )
                    db.session.add(adm_account)

                    # Create admin info
                    emp_info = EmployeeInfo.query.filter_by(
                        employee_number=application.employee_number
                    ).first()
                    if emp_info:
                        adm_info = AdmInfo(
                            adm_number=application.employee_number,
                            name=emp_info.name,
                            create_time=datetime.utcnow()
                        )
                        db.session.add(adm_info)

            elif result is False:
                application.status = 'rejected'
                application.closed_at = datetime.utcnow()
                application.closed_by = voter_number

            db.session.commit()

            return {
                'status': True,
                'msg': f'投票成功，{reason}',
                'data': application.to_dict()
            }, 200

        except Exception as e:
            db.session.rollback()
            logging.error(str(e))
            return {'status': False, 'msg': '投票失败，请稍后重试'}, 500


class AdminApplicationCloseResource(Resource):
    """手动结束投票"""
    @jwt_required()
    def post(self, application_id):
        identity = get_jwt_identity()

        if not is_admin_role(identity.get('role')):
            return {'status': False, 'msg': '只有管理员可以操作'}, 403

        application = AdminApplication.query.get(application_id)
        if not application:
            return {'status': False, 'msg': '申请不存在'}, 404

        if application.status not in ['pending', 'voting']:
            return {'status': False, 'msg': '该申请已结束'}, 400

        total_admins = AdmAccount.query.count()
        result, reason = application.check_threshold(total_admins)

        try:
            if result is True:
                application.status = 'approved'
                # Create admin account (same logic as vote)
                emp_account = EmployeeAccount.query.filter_by(
                    employee_number=application.employee_number
                ).first()
                if emp_account:
                    adm_account = AdmAccount(
                        adm_user_name=emp_account.employee_user_name,
                        adm_user_password=emp_account.employee_user_password,
                        role='admin',
                        adm_number=application.employee_number
                    )
                    db.session.add(adm_account)

                    emp_info = EmployeeInfo.query.filter_by(
                        employee_number=application.employee_number
                    ).first()
                    if emp_info:
                        adm_info = AdmInfo(
                            adm_number=application.employee_number,
                            name=emp_info.name,
                            create_time=datetime.utcnow()
                        )
                        db.session.add(adm_info)

            else:
                application.status = 'rejected'

            application.closed_at = datetime.utcnow()
            application.closed_by = identity.get('number')

            db.session.commit()

            return {
                'status': True,
                'msg': f'审核已结束: {reason}',
                'data': application.to_dict()
            }, 200

        except Exception as e:
            db.session.rollback()
            logging.error(str(e))
            return {'status': False, 'msg': '操作失败'}, 500