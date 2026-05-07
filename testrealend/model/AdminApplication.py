from datetime import datetime
from extension.extension import db
import json


class AdminApplication(db.Model):
    """管理员申请模型 - 员工申请成为管理员"""
    __bind_key__ = 'mysql_db'
    __tablename__ = 'admin_application'

    id = db.Column(db.Integer, primary_key=True)

    # Applicant Info
    employee_number = db.Column(db.String(255), db.ForeignKey('employee_info.employee_number'), nullable=False)
    employee_name = db.Column(db.String(255), nullable=False)

    # Application Details
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='pending')  # 'pending', 'voting', 'approved', 'rejected'

    # Voting
    votes_json = db.Column(db.Text, nullable=True)  # JSON: {"adm_number": {"vote": true/false, "comment": "..."}}
    total_votes = db.Column(db.Integer, default=0)
    approve_votes = db.Column(db.Integer, default=0)
    reject_votes = db.Column(db.Integer, default=0)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)
    closed_by = db.Column(db.String(255), nullable=True)

    # Relationship
    employee = db.relationship('EmployeeInfo', backref=db.backref('admin_applications', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'employee_number': self.employee_number,
            'employee_name': self.employee_name,
            'reason': self.reason,
            'status': self.status,
            'status_text': self._get_status_text(),
            'votes_json': json.loads(self.votes_json) if self.votes_json else {},
            'total_votes': self.total_votes,
            'approve_votes': self.approve_votes,
            'reject_votes': self.reject_votes,
            'approval_ratio': round(self.approve_votes / max(self.total_votes, 1) * 100, 1),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
            'closed_at': self.closed_at.strftime('%Y-%m-%d %H:%M:%S') if self.closed_at else None
        }

    def _get_status_text(self):
        status_map = {
            'pending': '待审核',
            'voting': '投票中',
            'approved': '已通过',
            'rejected': '已拒绝'
        }
        return status_map.get(self.status, self.status)

    def add_vote(self, voter_number, voter_name, approve, comment=None):
        """Add a vote to the application"""
        votes = json.loads(self.votes_json) if self.votes_json else {}

        # Remove previous vote if exists
        if voter_number in votes:
            old_vote = votes[voter_number].get('approve')
            if old_vote:
                self.approve_votes -= 1
            else:
                self.reject_votes -= 1
            self.total_votes -= 1

        # Add new vote
        votes[voter_number] = {
            'name': voter_name,
            'approve': approve,
            'comment': comment or '',
            'time': datetime.utcnow().isoformat()
        }

        self.total_votes += 1
        if approve:
            self.approve_votes += 1
        else:
            self.reject_votes += 1

        self.votes_json = json.dumps(votes)

    def check_threshold(self, total_admins):
        """
        Check if the approval threshold is met.
        Need 66%+ approval to become admin.
        Returns: (approved: bool or None, reason: str)
        """
        if total_admins <= 0:
            return False, '没有管理员可投票'

        approval_ratio = self.approve_votes / total_admins

        # All admins have voted
        if self.total_votes >= total_admins:
            if approval_ratio >= 0.66:
                return True, f'超过66%同意({self.approve_votes}/{total_admins})'
            else:
                return False, f'未达到66%同意({self.approve_votes}/{total_admins})'

        # Check if threshold is already met
        if approval_ratio >= 0.66:
            return True, f'已达到66%同意({self.approve_votes}/{total_admins})'

        # Check if it's mathematically impossible to reach 66%
        remaining_voters = total_admins - self.total_votes
        max_possible_approve = self.approve_votes + remaining_voters

        if max_possible_approve / total_admins < 0.66:
            return False, '无法达到66%，申请被拒绝'

        return None, '投票进行中'