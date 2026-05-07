from datetime import datetime
from extension.extension import db
import json


class RecallProposal(db.Model):
    """数据回收提议模型"""
    __bind_key__ = 'mysql_db'
    __tablename__ = 'recall_proposal'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('application.id'), nullable=False)

    # Proposer Info
    proposer_number = db.Column(db.String(255), nullable=False)
    proposer_name = db.Column(db.String(255), nullable=False)
    proposer_role = db.Column(db.String(50), nullable=False)  # 'adm1', 'adm2', 'adm3'

    # Proposal Details
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='voting')  # 'voting', 'approved', 'rejected', 'cancelled'

    # Vote Counts
    votes_for = db.Column(db.Integer, default=0)
    votes_against = db.Column(db.Integer, default=0)
    votes_abstain = db.Column(db.Integer, default=0)
    votes_json = db.Column(db.Text, nullable=True)  # JSON: {"adm1": "for", "adm2": "against", ...}

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    voting_deadline = db.Column(db.DateTime, nullable=True)
    closed_at = db.Column(db.DateTime, nullable=True)
    closed_by = db.Column(db.String(255), nullable=True)

    # Relationship
    application = db.relationship('Application', backref=db.backref('recall_proposals', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'application_id': self.application_id,
            'proposer_number': self.proposer_number,
            'proposer_name': self.proposer_name,
            'proposer_role': self.proposer_role,
            'reason': self.reason,
            'status': self.status,
            'status_text': self._get_status_text(),
            'votes_for': self.votes_for,
            'votes_against': self.votes_against,
            'votes_abstain': self.votes_abstain,
            'votes_json': json.loads(self.votes_json) if self.votes_json else {},
            'total_votes': self.votes_for + self.votes_against + self.votes_abstain,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'voting_deadline': self.voting_deadline.strftime('%Y-%m-%d %H:%M:%S') if self.voting_deadline else None,
            'closed_at': self.closed_at.strftime('%Y-%m-%d %H:%M:%S') if self.closed_at else None
        }

    def _get_status_text(self):
        status_map = {
            'voting': '投票中',
            'approved': '已通过回收',
            'rejected': '已否决',
            'cancelled': '已取消'
        }
        return status_map.get(self.status, self.status)

    def add_vote(self, voter_number, voter_name, vote_type):
        """Add a vote to the proposal"""
        votes = json.loads(self.votes_json) if self.votes_json else {}

        # Remove previous vote if exists
        if voter_number in votes:
            old_vote = votes[voter_number].get('vote')
            if old_vote == 'for':
                self.votes_for -= 1
            elif old_vote == 'against':
                self.votes_against -= 1
            elif old_vote == 'abstain':
                self.votes_abstain -= 1

        # Add new vote
        votes[voter_number] = {
            'name': voter_name,
            'vote': vote_type,
            'time': datetime.utcnow().isoformat()
        }

        if vote_type == 'for':
            self.votes_for += 1
        elif vote_type == 'against':
            self.votes_against += 1
        elif vote_type == 'abstain':
            self.votes_abstain += 1

        self.votes_json = json.dumps(votes)

    def check_threshold(self, total_admins, exclude_proposer=True):
        """
        Check if the recall threshold is met.
        Returns: (should_recall: bool, reason: str)
        """
        # Total eligible voters (exclude proposer)
        eligible_voters = total_admins - 1 if exclude_proposer else total_admins

        # Need 50%+ against to recall
        if eligible_voters <= 0:
            return False, '没有足够的投票人'

        against_ratio = self.votes_against / eligible_voters

        # Check if voting should be closed
        total_voted = self.votes_for + self.votes_against + self.votes_abstain

        if against_ratio > 0.5:
            return True, f'超过50%反对({self.votes_against}/{eligible_voters})'

        # Check if it's mathematically impossible to reach 50% against
        remaining_voters = eligible_voters - total_voted
        max_possible_against = self.votes_against + remaining_voters

        if max_possible_against / eligible_voters <= 0.5:
            return False, '反对票无法达到50%，回收提议被否决'

        return None, '投票进行中'
