from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone, timedelta
import logging
from utils.required import is_admin_role
import json

from extension.extension import db
from model.Application import Application
from model.RecallProposal import RecallProposal
from model.Adm_Account import AdmAccount
from model.Adm_Info import AdmInfo
from model.EmployeeNotification import EmployeeNotification
from utils.log_helper import log_action


class RecallListResource(Resource):
    """
    Get recall proposals list
    ---
    tags: [Recall]
    security: [Bearer: []]
    parameters:
      - in: query
        name: page
        type: integer
        default: 1
      - in: query
        name: pageSize
        type: integer
        default: 10
      - in: query
        name: status
        type: string
        description: Filter by status (open/closed/approved/rejected)
    responses:
      200: {description: Recall proposals list}
    """
    @jwt_required()
    def get(self):
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('pageSize', 10, type=int)
        status_filter = request.args.get('status')

        query = RecallProposal.query.order_by(RecallProposal.created_at.desc())

        if status_filter:
            query = query.filter_by(status=status_filter)

        pagination = query.paginate(page=page, per_page=page_size, error_out=False)

        items = []
        for item in pagination.items:
            data = item.to_dict()
            # Add application info
            app = db.session.get(Application, item.application_id)
            if app:
                data['application_info'] = {
                    'data_alias': app.data_alias,
                    'applicant_name': app.applicant_name,
                    'applicant_user_number': app.applicant_user_number
                }
            items.append(data)

        return {
            'status': True,
            'data': {
                'list': items,
                'total': pagination.total
            }
        }, 200


class RecallCreateResource(Resource):
    """创建回收提议"""
    @jwt_required()
    def post(self):
        identity = get_jwt_identity()
        proposer_number = identity.get('number')
        proposer_name = identity.get('username')
        proposer_role = identity.get('role')

        if not is_admin_role(proposer_role):
            return {'status': False, 'msg': '只有管理员可以发起回收提议'}, 403

        data = request.get_json() or {}
        application_id = data.get('application_id')
        reason = (data.get('reason') or '').strip()

        if not application_id:
            return {'status': False, 'msg': '缺少申请ID'}, 400

        if len(reason) < 20:
            return {'status': False, 'msg': '回收原因至少需要20个字符'}, 400

        # Check if application exists and is approved
        app = db.session.get(Application, application_id)
        if not app:
            return {'status': False, 'msg': '申请不存在'}, 404

        if app.adm1_statu != True or app.adm2_statu != True:
            return {'status': False, 'msg': '只能回收已批准的申请'}, 400

        if app.is_recalled:
            return {'status': False, 'msg': '该数据已被回收'}, 400

        # Check if there's already an active recall proposal
        existing = RecallProposal.query.filter_by(
            application_id=application_id,
            status='voting'
        ).first()
        if existing:
            return {'status': False, 'msg': '该申请已有正在投票的回收提议'}, 400

        # Get proposer name from database if not in identity
        if not proposer_name:
            adm_info = AdmInfo.query.filter_by(adm_number=proposer_number).first()
            proposer_name = adm_info.name if adm_info else proposer_number

        # Create proposal with 7-day voting deadline
        proposal = RecallProposal(
            application_id=application_id,
            proposer_number=proposer_number,
            proposer_name=proposer_name,
            proposer_role=proposer_role,
            reason=reason,
            status='voting',
            voting_deadline=datetime.now(timezone.utc) + timedelta(days=7)
        )

        try:
            db.session.add(proposal)
            db.session.commit()
            log_action(proposer_number, proposer_name, '回收提议创建', '成功',
                       f"app_id={application_id}")
            return {
                'status': True,
                'msg': '回收提议创建成功',
                'data': proposal.to_dict()
            }, 201
        except Exception as e:
            db.session.rollback()
            logging.error(str(e))
            return {'status': False, 'msg': '创建失败，请稍后重试'}, 500


class RecallVoteResource(Resource):
    """投票回收提议"""
    @jwt_required()
    def post(self, proposal_id):
        identity = get_jwt_identity()
        voter_number = identity.get('number')
        voter_role = identity.get('role')

        if not is_admin_role(voter_role):
            return {'status': False, 'msg': '只有管理员可以投票'}, 403

        proposal = db.session.get(RecallProposal, proposal_id)
        if not proposal:
            return {'status': False, 'msg': '提议不存在'}, 404

        if proposal.status != 'voting':
            return {'status': False, 'msg': '该提议已结束投票'}, 400

        # Proposer cannot vote on their own proposal
        if voter_number == proposal.proposer_number:
            return {'status': False, 'msg': '提议人不能投票自己的提议'}, 400

        # Check voting deadline
        if proposal.voting_deadline and datetime.now(timezone.utc) > proposal.voting_deadline:
            # Auto-close the proposal
            proposal.status = 'rejected'
            proposal.closed_at = datetime.now(timezone.utc)
            db.session.commit()
            return {'status': False, 'msg': '投票已截止'}, 400

        data = request.get_json() or {}
        vote_type = data.get('vote')  # 'for', 'against', 'abstain'

        if vote_type not in ['for', 'against', 'abstain']:
            return {'status': False, 'msg': '无效的投票类型'}, 400

        # Get voter name
        voter_name = identity.get('username')
        if not voter_name:
            adm_info = AdmInfo.query.filter_by(adm_number=voter_number).first()
            voter_name = adm_info.name if adm_info else voter_number

        proposal.add_vote(voter_number, voter_name, vote_type)

        # Check threshold
        total_admins = AdmAccount.query.count()
        result, reason = proposal.check_threshold(total_admins, exclude_proposer=True)

        try:
            if result is True:
                # Recall approved - mark application as recalled
                proposal.status = 'approved'
                proposal.closed_at = datetime.now(timezone.utc)
                proposal.closed_by = voter_number

                app = db.session.get(Application, proposal.application_id)
                app.is_recalled = True
                app.recalled_at = datetime.now(timezone.utc)
                app.recall_reason = proposal.reason
                app.download_enabled = False

                # Notify the applicant
                notification = EmployeeNotification(
                    user_number=app.applicant_user_number,
                    title='数据回收通知',
                    content=f'您的数据申请(ID: {app.id})已被回收。原因: {proposal.reason}',
                    sender_number='system',
                    sender_name='系统'
                )
                db.session.add(notification)

            elif result is False:
                # Recall rejected
                proposal.status = 'rejected'
                proposal.closed_at = datetime.now(timezone.utc)
                proposal.closed_by = voter_number

            db.session.commit()

            log_action(voter_number, voter_name, '回收投票', '成功',
                       f"proposal_id={proposal_id} vote={vote_type} result={result}")

            return {
                'status': True,
                'msg': f'投票成功，当前状态: {reason}',
                'data': proposal.to_dict()
            }, 200

        except Exception as e:
            db.session.rollback()
            logging.error(str(e))
            return {'status': False, 'msg': '投票失败，请稍后重试'}, 500


class RecallDetailResource(Resource):
    """获取回收提议详情"""
    @jwt_required()
    def get(self, proposal_id):
        proposal = db.session.get(RecallProposal, proposal_id)
        if not proposal:
            return {'status': False, 'msg': '提议不存在'}, 404

        data = proposal.to_dict()

        # Add application info
        app = db.session.get(Application, proposal.application_id)
        if app:
            data['application'] = app.to_dict()

        # Add current user's vote status
        identity = get_jwt_identity()
        voter_number = identity.get('number')
        votes = json.loads(proposal.votes_json) if proposal.votes_json else {}
        data['my_vote'] = votes.get(voter_number, {}).get('vote', None)
        data['can_vote'] = (
            is_admin_role(identity.get('role')) and
            voter_number != proposal.proposer_number and
            proposal.status == 'voting'
        )

        return {'status': True, 'data': data}, 200


class RecallCloseResource(Resource):
    """手动结束投票"""
    @jwt_required()
    def post(self, proposal_id):
        identity = get_jwt_identity()

        proposal = db.session.get(RecallProposal, proposal_id)
        if not proposal:
            return {'status': False, 'msg': '提议不存在'}, 404

        if proposal.status != 'voting':
            return {'status': False, 'msg': '该提议已结束'}, 400

        # Only proposer or admin can close
        if not is_admin_role(identity.get('role')):
            return {'status': False, 'msg': '只有管理员可以结束投票'}, 403

        total_admins = AdmAccount.query.count()
        result, reason = proposal.check_threshold(total_admins, exclude_proposer=True)

        try:
            if result is True:
                proposal.status = 'approved'
                app = db.session.get(Application, proposal.application_id)
                app.is_recalled = True
                app.recalled_at = datetime.now(timezone.utc)
                app.recall_reason = proposal.reason
                app.download_enabled = False

                notification = EmployeeNotification(
                    user_number=app.applicant_user_number,
                    title='数据回收通知',
                    content=f'您的数据申请(ID: {app.id})已被回收。原因: {proposal.reason}',
                    sender_number='system',
                    sender_name='系统'
                )
                db.session.add(notification)

            else:
                proposal.status = 'rejected'

            proposal.closed_at = datetime.now(timezone.utc)
            proposal.closed_by = identity.get('number')

            db.session.commit()

            log_action(identity.get('number'), identity.get('username', 'admin'),
                       '回收投票关闭', '成功',
                       f"proposal_id={proposal_id} result={result}")

            return {
                'status': True,
                'msg': f'投票已结束: {reason}',
                'data': proposal.to_dict()
            }, 200

        except Exception as e:
            db.session.rollback()
            logging.error(str(e))
            return {'status': False, 'msg': '操作失败'}, 500


class RecallHistoryResource(Resource):
    """获取某个申请的回收历史"""
    @jwt_required()
    def get(self, application_id):
        proposals = RecallProposal.query.filter_by(application_id=application_id).order_by(RecallProposal.created_at.desc()).all()
        return {
            'status': True,
            'data': [p.to_dict() for p in proposals]
        }, 200