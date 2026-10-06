"""Tests for recall proposal endpoints."""

from datetime import UTC, datetime, timedelta


class TestRecallProposals:
    def test_list_requires_auth(self, client):
        resp = client.get("/api/recall/list")
        assert resp.status_code in (401, 422)

    def test_list_recalls(self, client, auth_headers):
        resp = client.get("/api/recall/list", headers=auth_headers)
        assert resp.status_code == 200

    def test_create_recall_requires_auth(self, client):
        resp = client.post("/api/recall/create", json={"application_id": 1, "reason": "test"})
        assert resp.status_code in (401, 422)

    def test_create_recall_missing_fields(self, client, auth_headers):
        resp = client.post("/api/recall/create", headers=auth_headers, json={})
        assert resp.status_code in (400, 404, 422)

    def test_vote_requires_auth(self, client):
        resp = client.post("/api/recall/1/vote", json={"vote": "agree"})
        assert resp.status_code in (401, 422)

    def test_detail_requires_auth(self, client):
        resp = client.get("/api/recall/1")
        assert resp.status_code in (401, 422)

    def test_nonexistent_recall(self, client, auth_headers):
        resp = client.get("/api/recall/99999", headers=auth_headers)
        assert resp.status_code in (404, 200)


class TestRecallVotingChain:
    """Regression (API campaign domain07): every non-proposer vote raised
    ``TypeError: can't compare offset-naive and offset-aware datetimes``
    (recall_resource.py compared ``datetime.now(UTC)`` against the naive DB
    ``voting_deadline``) and returned 500, so the whole threshold chain —
    approve -> recall -> notify -> download blocked -> restore — was
    unreachable. The full chain must work end to end."""

    @staticmethod
    def _seed_approved_application(db):
        from model.Application import Application

        item = Application(
            data_id=1,
            data_name="recall-demo",
            data_alias="recall-demo",
            data_type="vector",
            applicant_name="员工1",
            applicant_user_number="E001",
            reason="recall regression chain",
            adm1_statu=True,
            adm2_statu=True,
        )
        db.session.add(item)
        db.session.commit()
        return item

    @staticmethod
    def _create_proposal(client, auth_headers, application_id):
        resp = client.post(
            "/api/recall/create",
            headers=auth_headers,
            json={"application_id": application_id, "reason": "regression recall reason (at least 20 chars)"},
        )
        assert resp.status_code == 201, resp.get_data(as_text=True)
        return resp.get_json()["data"]["id"]

    def test_vote_chain_approves_recall_and_restore(self, client, db, auth_headers, adm2_headers, adm3_headers):
        from model.Application import Application
        from model.EmployeeNotification import EmployeeNotification

        item = self._seed_approved_application(db)
        proposal_id = self._create_proposal(client, auth_headers, item.id)

        # First non-proposer vote must not 500 (pre-fix: TypeError).
        v1 = client.post(f"/api/recall/{proposal_id}/vote", headers=adm2_headers, json={"vote": "against"})
        assert v1.status_code == 200, v1.get_data(as_text=True)
        assert v1.get_json()["data"]["status"] == "voting"

        # Second non-proposer vote reaches >50% against -> proposal approved.
        v2 = client.post(f"/api/recall/{proposal_id}/vote", headers=adm3_headers, json={"vote": "against"})
        assert v2.status_code == 200, v2.get_data(as_text=True)
        assert v2.get_json()["data"]["status"] == "approved"

        db.session.expire_all()
        app_row = db.session.get(Application, item.id)
        assert app_row.is_recalled is True
        assert app_row.download_enabled is False
        assert app_row.recalled_at is not None
        assert app_row.recall_reason

        recall_notices = EmployeeNotification.query.filter_by(user_number="E001", title="数据回收通知").all()
        assert any(str(item.id) in (n.content or "") for n in recall_notices)

        # A finished proposal can no longer be closed.
        close = client.post(f"/api/recall/{proposal_id}/close", headers=adm3_headers)
        assert close.status_code == 400

        restore = client.post(
            "/api/recall/restore",
            headers=auth_headers,
            json={"application_id": item.id, "reason": "regression restore reason"},
        )
        assert restore.status_code == 200, restore.get_data(as_text=True)
        db.session.expire_all()
        app_row = db.session.get(Application, item.id)
        assert app_row.is_recalled is False
        assert app_row.download_enabled is True
        assert app_row.recalled_at is None

        restore_notices = EmployeeNotification.query.filter_by(user_number="E001", title="数据恢复通知").all()
        assert any(str(item.id) in (n.content or "") for n in restore_notices)

    def test_expired_deadline_auto_closes_and_blocks_vote(self, client, db, auth_headers, adm2_headers):
        from model.RecallProposal import RecallProposal

        item = self._seed_approved_application(db)
        proposal_id = self._create_proposal(client, auth_headers, item.id)

        # Simulate a deadline that already passed: DB round-trips store naive
        # UTC values, which is exactly the shape that used to raise TypeError.
        proposal = db.session.get(RecallProposal, proposal_id)
        proposal.voting_deadline = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1)
        db.session.commit()

        resp = client.post(f"/api/recall/{proposal_id}/vote", headers=adm2_headers, json={"vote": "against"})
        assert resp.status_code == 400, resp.get_data(as_text=True)
        assert "截止" in resp.get_json()["msg"]

        db.session.expire_all()
        proposal = db.session.get(RecallProposal, proposal_id)
        assert proposal.status == "rejected"
        assert proposal.closed_at is not None
