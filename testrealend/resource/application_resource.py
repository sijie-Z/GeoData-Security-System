from flask import request, Response
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from model.Application import Application
from extension.extension import db, limiter
from datetime import datetime
import base64
import logging
from utils.log_helper import log_action
from utils.metrics import record_application, record_approval
from utils.user_limiter import normal_limit, relaxed_limit
from utils.websocket import notify_application_update, notify_new_application
from utils.cache import invalidate_prefix
from utils.required import admin_required, admin_role_required

def _build_application_status(item):
    if item.is_recalled:
        return 'recalled'
    if item.adm2_statu is True:
        return 'approved'
    if item.adm2_statu is False:
        return 'rejected'
    if item.adm1_statu is True:
        return 'adm1_approved'
    if item.adm1_statu is False:
        return 'adm1_rejected'
    return 'pending'


def _to_dual_channel_dict(item):
    return {
        'id': item.id,
        'data_alias': item.data_alias,
        'data_id': item.data_id,
        'data_type': item.data_type,
        'applicant_name': item.applicant_name,
        'applicant_user_number': item.applicant_user_number,
        'reason': item.reason,
        'application_time': item.application_submission_time.strftime('%Y-%m-%d %H:%M:%S') if item.application_submission_time else None,
        'first_statu': item.adm1_statu,
        'first_reviewer': item.adm1_name,
        'first_review_time': item.adm1_approval_time.isoformat() if item.adm1_approval_time else None,
        'second_statu': item.adm2_statu,
        'second_reviewer': item.adm2_name,
        'second_review_time': item.adm2_approval_time.isoformat() if item.adm2_approval_time else None,
        'status': _build_application_status(item)
    }


def _review_actor():
    """Get reviewer identity from JWT token (not from request body)."""
    from model.Adm_Info import AdmInfo
    identity = get_jwt_identity() or {}
    user_number = str(identity.get('number', ''))
    user_name = identity.get('username', '')
    if not user_name and user_number:
        adm = AdmInfo.query.filter_by(adm_number=user_number).first()
        if adm:
            user_name = adm.name
    return user_name, user_number


def _validate_stage_transition(item, stage):
    if stage == 'adm1':
        if item.adm1_statu is not None:
            return False, '该申请已完成一审，不能重复操作'
        if item.adm2_statu is not None:
            return False, '该申请已存在二审结果，不能再执行一审'
        return True, ''
    if stage == 'adm2':
        if item.adm1_statu is not True:
            return False, '该申请尚未通过一审，不能执行二审'
        if item.adm2_statu is not None:
            return False, '该申请已完成二审，不能重复操作'
        return True, ''
    return False, '无效审核阶段'


def _update_review_result(item, stage, passed, user_name, user_number):
    if stage == 'adm1':
        item.adm1_statu = bool(passed)
        item.adm1_name = user_name
        item.adm1_user_number = user_number
        item.adm1_approval_time = datetime.utcnow()
        return
    item.adm2_statu = bool(passed)
    item.adm2_name = user_name
    item.adm2_user_number = user_number
    item.adm2_approval_time = datetime.utcnow()


class SubmitApplicationResource(Resource):
    """
    提交数据申请
    ---
    tags: [Application]
    security: [Bearer: []]
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [data_id, data_name, data_alias, applicant_name, applicant_user_number]
          properties:
            data_id: {type: integer, description: 数据ID}
            data_name: {type: string, description: 数据名称}
            data_alias: {type: string, description: 数据别名}
            data_url: {type: string, description: 数据URL}
            data_type: {type: string, enum: [vector, raster], description: 数据类型}
            applicant_name: {type: string, description: 申请人姓名}
            applicant_user_number: {type: string, description: 申请人工号}
            reason: {type: string, description: 申请理由}
    responses:
      201: {description: 申请提交成功}
      500: {description: 操作失败}
    """
    @jwt_required()
    @limiter.limit("20 per minute")
    def post(self):
        data = request.get_json()
        # Get identity from JWT to prevent impersonation
        identity = get_jwt_identity()
        if isinstance(identity, dict):
            jwt_name = identity.get('name', '')
            jwt_number = identity.get('number', '')
        else:
            jwt_name = data.get('applicant_name', '')
            jwt_number = str(identity)
        new_app = Application(
            data_id=data.get('data_id'),
            data_name=data.get('data_name'),
            data_alias=data.get('data_alias'),
            data_url=data.get('data_url'),
            data_type=data.get('data_type', 'vector').lower(), # Default to vector
            applicant_name=jwt_name,
            applicant_user_number=jwt_number,
            reason=data.get('reason'),
            application_submission_time=datetime.utcnow()
        )
        try:
            db.session.add(new_app)
            db.session.commit()
            log_action(
                new_app.applicant_user_number,
                new_app.applicant_name,
                '申请提交',
                '成功',
                f"data_id={new_app.data_id} data_alias={new_app.data_alias}"
            )
            record_application(data_type=new_app.data_type or 'unknown')
            notify_new_application(new_app.id, new_app.applicant_name, new_app.data_alias)
            invalidate_prefix('dashboard')
            return {'status': True, 'msg': '申请提交成功'}, 201
        except Exception as e:
            db.session.rollback()
            logging.error(str(e))
            return {'status': False, 'msg': '操作失败，请稍后重试'}, 500


class WithdrawApplicationResource(Resource):
    """Withdraw (cancel) a pending application."""
    @jwt_required()
    @normal_limit
    def put(self, application_id):
        identity = get_jwt_identity() or {}
        user_number = identity.get('number')
        item = Application.query.get(application_id)
        if not item:
            return {'status': False, 'msg': '申请不存在'}, 404
        if item.applicant_user_number != user_number:
            return {'status': False, 'msg': '只能撤回自己的申请'}, 403
        if item.is_recalled:
            return {'status': False, 'msg': '该申请已撤回'}, 400
        if item.adm1_statu is not None:
            return {'status': False, 'msg': '该申请已在审批中，无法撤回'}, 400

        item.is_recalled = True
        item.recalled_at = datetime.utcnow()
        item.recall_reason = '申请人主动撤回'
        db.session.commit()

        log_action(user_number, item.applicant_name, '撤回申请', '成功',
                   f"app_id={item.id} data_alias={item.data_alias}")
        invalidate_prefix('dashboard')
        return {'status': True, 'msg': '申请已撤回'}, 200


class GetApplicationsResource(Resource):
    @jwt_required()
    @relaxed_limit
    def get(self):
        identity = get_jwt_identity() or {}
        user_number = identity.get('number') or request.args.get('userNumber')
        page = request.args.get('page', 1, type=int)
        page_size = min(request.args.get('pageSize', 10, type=int), 100)
        
        query = Application.query.filter_by(applicant_user_number=user_number)
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)
        
        items = [{
            'id': item.id,
            'data_alias': item.data_alias,
            'data_id': item.data_id,
            'reason': item.reason,
            'first_statu': item.adm1_statu,
            'second_statu': item.adm2_statu
        } for item in pagination.items]
        
        return {
            'status': True,
            'emp_get_applications': items,
            'pages': {'total': pagination.total}
        }, 200

class ApprovedApplicationsResource(Resource):
    @jwt_required()
    def get(self):
        identity = get_jwt_identity() or {}
        user_number = identity.get('number') or request.args.get('userNumber')
        page = request.args.get('page', 1, type=int)
        page_size = min(request.args.get('pageSize', 5, type=int), 100)
        
        # Only applications that passed both reviews
        query = Application.query.filter_by(applicant_user_number=user_number, adm1_statu=True, adm2_statu=True)
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)
        
        items = [{
            'application_id': item.id,
            'data_alias': item.data_alias,
            'data_id': item.data_id,
            'applicant_user_number': item.applicant_user_number,
            'applicant_name': item.applicant_name,
            'send_file_person_user_number': item.adm2_user_number or 'Admin'
        } for item in pagination.items]
        
        return {
            'status': True,
            'emp_get_applications': items,
            'pages': {'total': pagination.total}
        }, 200

class Adm1GetApplicationsResource(Resource):
    @jwt_required()
    def get(self):
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('pageSize', 10, type=int)
        
        # Admin 1 reviews applications that haven't been reviewed yet
        query = Application.query.filter(Application.adm1_statu == None)
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)
        
        items = [{
            'id': item.id,
            'data_alias': item.data_alias,
            'data_id': item.data_id,
            'applicant_user_number': item.applicant_user_number,
            'applicant_name': item.applicant_name,
            'reason': item.reason
        } for item in pagination.items]
        
        return {
            'status': True,
            'application_data': items,
            'pages': {'total': pagination.total}
        }, 200

class Adm2GetApprovedResource(Resource):
    @jwt_required()
    def get(self):
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('pageSize', 10, type=int)
        
        # Admin 2 reviews applications that passed Admin 1 but haven't been reviewed by Admin 2
        query = Application.query.filter(Application.adm1_statu == True, Application.adm2_statu == None)
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)
        
        items = [{
            'id': item.id,
            'data_alias': item.data_alias,
            'data_id': item.data_id,
            'applicant_user_number': item.applicant_user_number,
            'applicant_name': item.applicant_name,
            'reason': item.reason,
            'first_statu': item.adm1_statu
        } for item in pagination.items]
        
        return {
            'status': True,
            'approved_application_data': items,
            'pages': {'total': pagination.total}
        }, 200

class Adm1PassResource(Resource):
    @admin_role_required('admin1')
    @normal_limit
    def post(self):
        data = request.get_json() or {}
        app_id = data.get('id') or data.get('application_id')
        item = Application.query.get(app_id)
        if item:
            ok, msg = _validate_stage_transition(item, 'adm1')
            if not ok:
                return {'status': False, 'msg': msg}, 400
            user_name, user_number = _review_actor()
            _update_review_result(item, 'adm1', True, user_name, user_number)
            db.session.commit()
            log_action(user_number, user_name, '一审通过', '成功',
                       f"app_id={item.id} data_alias={item.data_alias}")
            record_approval(result='approved', level='adm1')
            notify_application_update(item.id, 'adm1_approved', item.applicant_user_number)
            invalidate_prefix('dashboard')
            return {'status': True, 'msg': '一审通过', 'application': _to_dual_channel_dict(item)}, 200
        return {'status': False, 'msg': '申请不存在'}, 404

class Adm1FailResource(Resource):
    @admin_role_required('admin1')
    def post(self):
        data = request.get_json() or {}
        app_id = data.get('id') or data.get('application_id')
        item = Application.query.get(app_id)
        if item:
            ok, msg = _validate_stage_transition(item, 'adm1')
            if not ok:
                return {'status': False, 'msg': msg}, 400
            user_name, user_number = _review_actor()
            _update_review_result(item, 'adm1', False, user_name, user_number)
            db.session.commit()
            log_action(user_number, user_name, '一审驳回', '成功',
                       f"app_id={item.id} data_alias={item.data_alias}")
            record_approval(result='rejected', level='adm1')
            notify_application_update(item.id, 'adm1_rejected', item.applicant_user_number)
            invalidate_prefix('dashboard')
            return {'status': True, 'msg': '一审驳回', 'application': _to_dual_channel_dict(item)}, 200
        return {'status': False, 'msg': '申请不存在'}, 404

class Adm2PassResource(Resource):
    @admin_role_required('admin2')
    @normal_limit
    def post(self):
        data = request.get_json() or {}
        app_id = data.get('id') or data.get('application_id')
        item = Application.query.get(app_id)
        if item:
            ok, msg = _validate_stage_transition(item, 'adm2')
            if not ok:
                return {'status': False, 'msg': msg}, 400
            user_name, user_number = _review_actor()
            _update_review_result(item, 'adm2', True, user_name, user_number)
            db.session.commit()
            log_action(user_number, user_name, '二审通过', '成功',
                       f"app_id={item.id} data_alias={item.data_alias}")
            record_approval(result='approved', level='adm2')
            notify_application_update(item.id, 'approved', item.applicant_user_number)
            invalidate_prefix('dashboard')
            return {'status': True, 'msg': '二审通过', 'application': _to_dual_channel_dict(item)}, 200
        return {'status': False, 'msg': '申请不存在'}, 404

class Adm2FailResource(Resource):
    @admin_role_required('admin2')
    def post(self):
        data = request.get_json() or {}
        app_id = data.get('id') or data.get('application_id')
        item = Application.query.get(app_id)
        if item:
            ok, msg = _validate_stage_transition(item, 'adm2')
            if not ok:
                return {'status': False, 'msg': msg}, 400
            user_name, user_number = _review_actor()
            _update_review_result(item, 'adm2', False, user_name, user_number)
            db.session.commit()
            log_action(user_number, user_name, '二审驳回', '成功',
                       f"app_id={item.id} data_alias={item.data_alias}")
            record_approval(result='rejected', level='adm2')
            notify_application_update(item.id, 'rejected', item.applicant_user_number)
            invalidate_prefix('dashboard')
            return {'status': True, 'msg': '二审驳回', 'application': _to_dual_channel_dict(item)}, 200
        return {'status': False, 'msg': '申请不存在'}, 404

class BatchReviewResource(Resource):
    @admin_required
    @normal_limit
    def post(self):
        data = request.get_json() or {}
        ids = data.get('ids', [])
        stage = data.get('stage') # 'adm1' or 'adm2'
        action = data.get('action') # 'pass' or 'fail'
        user_name, user_number = _review_actor()
        if stage not in ('adm1', 'adm2'):
            return {'status': False, 'msg': '无效审核阶段'}, 400
        if action not in ('pass', 'fail'):
            return {'status': False, 'msg': '无效审核动作'}, 400
        if not isinstance(ids, list) or not ids:
            return {'status': False, 'msg': '缺少有效申请编号列表'}, 400
        apps = Application.query.filter(Application.id.in_(ids)).all()
        app_map = {app.id: app for app in apps}
        updated = []
        skipped = []
        now = datetime.utcnow()
        passed = action == 'pass'
        for app_id in ids:
            app = app_map.get(app_id)
            if not app:
                skipped.append({'id': app_id, 'reason': '申请不存在'})
                continue
            ok, msg = _validate_stage_transition(app, stage)
            if not ok:
                skipped.append({'id': app.id, 'reason': msg})
                continue
            if stage == 'adm1':
                app.adm1_statu = passed
                app.adm1_name = user_name
                app.adm1_user_number = user_number
                app.adm1_approval_time = now
            else:
                app.adm2_statu = passed
                app.adm2_name = user_name
                app.adm2_user_number = user_number
                app.adm2_approval_time = now
            updated.append(app.id)
        if updated:
            db.session.commit()
        msg = f'批量处理完成，成功{len(updated)}条，跳过{len(skipped)}条'
        return {
            'status': True,
            'msg': msg,
            'updated_ids': updated,
            'skipped': skipped
        }, 200

class ReReviewResource(Resource):
    @admin_required
    def post(self):
        data = request.get_json() or {}
        app_id = data.get('id') or data.get('application_id')
        stage = data.get('stage')
        statu = data.get('statu')
        user_name, user_number = _review_actor()
        item = Application.query.get(app_id)
        if item:
            if stage == 'adm2':
                if item.adm1_statu is not True:
                    return {'status': False, 'msg': '该申请尚未通过一审，不能复审二审结果'}, 400
                item.adm2_statu = statu
                item.adm2_name = user_name
                item.adm2_user_number = user_number
                item.adm2_approval_time = datetime.utcnow()
                db.session.commit()
                return {'status': True, 'msg': '二审结果提交成功', 'application': _to_dual_channel_dict(item)}, 200
        return {'status': False, 'msg': '提交失败'}, 400


class Adm3AdditionalReviewResource(Resource):
    @admin_role_required('admin3')
    def post(self):
        data = request.get_json() or {}
        app_id = data.get('id') or data.get('application_id')
        statu = data.get('statu', False)
        reason = data.get('reason')
        user_name, user_number = _review_actor()

        item = Application.query.get(app_id)
        if not item:
            return {'status': False, 'msg': '申请不存在'}, 404
        if item.adm2_statu is not True:
            return {'status': False, 'msg': '仅可对二审通过的申请进行附加审议'}, 400
        item.adm2_statu = bool(statu)
        item.adm2_name = user_name
        item.adm2_user_number = user_number
        item.adm2_approval_time = datetime.utcnow()
        if reason:
            item.reason = str(reason)
        db.session.commit()
        return {'status': True, 'msg': '附加审议已提交', 'application': _to_dual_channel_dict(item)}, 200


class Adm1GetShpApplicationsResource(Resource):
    @jwt_required()
    def get(self):
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('pageSize', 100, type=int)
        query = Application.query.filter(
            db.func.lower(db.func.coalesce(Application.data_type, 'vector')) == 'vector'
        ).order_by(Application.id.desc())
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)
        items = [_to_dual_channel_dict(item) for item in pagination.items]
        return {
            'status': True,
            'application_data': items,
            'pages': {'total': pagination.total}
        }, 200


class Adm1GetRasterApplicationsResource(Resource):
    @jwt_required()
    def get(self):
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('pageSize', 100, type=int)
        query = Application.query.filter(
            db.func.lower(db.func.coalesce(Application.data_type, '')) == 'raster'
        ).order_by(Application.id.desc())
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)
        items = [_to_dual_channel_dict(item) for item in pagination.items]
        return {
            'status': True,
            'application_data': items,
            'pages': {'total': pagination.total}
        }, 200


class ApplicationQRCodeResource(Resource):
    """获取申请的二维码数据"""
    @jwt_required()
    def get(self, application_id):
        item = Application.query.get(application_id)
        if not item:
            return {'status': False, 'msg': '申请不存在'}, 404
        
        qr_data = item.qrcode
        if not qr_data:
            return {'status': False, 'msg': '该申请尚未生成二维码'}, 404
        
        # 如果是bytes，转为base64
        if isinstance(qr_data, bytes):
            qr_base64 = base64.b64encode(qr_data).decode('utf-8')
        else:
            qr_base64 = qr_data
        
        return {
            'status': True,
            'data': {
                'application_id': item.id,
                'data_alias': item.data_alias,
                'qrcode': qr_base64,
                'qr_version': item.qr_version,
                'qr_signature': item.qr_signature,
                'generation_timestamp': item.generation_timestamp.isoformat() if item.generation_timestamp else None,
                'purpose': item.purpose,
                'usage_scope': item.usage_scope,
                'security_level': item.security_level
            }
        }, 200


class ApplicationQRCodeImageResource(Resource):
    """获取二维码图片（直接返回图片）"""
    @jwt_required()
    def get(self, application_id):
        item = Application.query.get(application_id)
        if not item:
            return {'status': False, 'msg': '申请不存在'}, 404
        
        qr_data = item.qrcode
        if not qr_data:
            return {'status': False, 'msg': '该申请尚未生成二维码'}, 404
        
        # 如果是base64字符串，解码
        if isinstance(qr_data, str):
            try:
                qr_bytes = base64.b64decode(qr_data)
            except:
                qr_bytes = qr_data.encode('utf-8')
        else:
            qr_bytes = qr_data
        
        return Response(
            qr_bytes,
            mimetype='image/png',
            headers={'Content-Disposition': f'inline; filename=qrcode_{application_id}.png'}
        )


class ApplicationDetailResource(Resource):
    """获取申请完整详情（包含二维码等）"""
    @jwt_required()
    def get(self, application_id):
        item = Application.query.get(application_id)
        if not item:
            return {'status': False, 'msg': '申请不存在'}, 404
        
        data = item.to_dict()
        
        # 添加额外信息
        data['status_text'] = {
            'pending': '待审批',
            'adm1_approved': '一审通过',
            'adm1_rejected': '一审驳回',
            'adm2_approved': '二审通过',
            'adm2_rejected': '二审驳回',
            'recalled': '已回收'
        }.get(item._get_status(), '未知')
        
        return {'status': True, 'data': data}, 200


class AllApplicationsResource(Resource):
    """获取所有申请列表（带筛选）"""
    @jwt_required()
    def get(self):
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('pageSize', 20, type=int)
        status = request.args.get('status')
        data_type = request.args.get('data_type')
        has_qrcode = request.args.get('has_qrcode')
        
        query = Application.query
        
        if status:
            if status == 'pending':
                query = query.filter(Application.adm1_statu == None)
            elif status == 'approved':
                query = query.filter(Application.adm2_statu == True)
            elif status == 'rejected':
                query = query.filter(
                    db.or_(Application.adm1_statu == False, Application.adm2_statu == False)
                )
        
        if data_type:
            query = query.filter(db.func.lower(Application.data_type) == data_type.lower())
        
        if has_qrcode == 'true':
            query = query.filter(Application.qrcode != None)
        elif has_qrcode == 'false':
            query = query.filter(Application.qrcode == None)
        
        query = query.order_by(Application.application_submission_time.desc())
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)
        
        items = [item.to_simple_dict() for item in pagination.items]
        
        return {
            'status': True,
            'data': {
                'list': items,
                'total': pagination.total,
                'page': page,
                'page_size': page_size
            }
        }, 200
