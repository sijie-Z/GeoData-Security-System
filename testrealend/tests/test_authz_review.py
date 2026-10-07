"""Authorization matrix for review/approval read endpoints (O1 authz review).

These endpoints used to carry only ``@jwt_required()``, so any logged-in user —
regular employees included — could read review/approval data.  They now carry
the same role gate as their write-side counterpart (the adm1/adm2 review
queues), the admin family gate (shared dual-channel console, recall
governance, promotion applications, batch-review export, employee management)
and the super admin (``role='admin'``) must always pass every gate.
"""

from datetime import UTC, datetime, timedelta

import pytest

ADMIN_ROLE_TO_FIXTURE = {
    "adm1": "auth_headers",
    "adm2": "adm2_headers",
    "adm3": "adm3_headers",
    "super": "superadmin_headers",
}

ALL_ADMINS = ["adm1", "adm2", "adm3", "super"]

# ``ok_roles`` lists the roles that must get 200; ``wrong_roles`` lists admin
# sub-roles that must get 403 (only the strict single-sub-role queues have
# wrong sub-roles — shared admin surfaces accept the whole admin family).
ENDPOINT_SPECS = [
    {
        "id": "adm1_review_queue",
        "method": "get",
        "path": "/api/adm1_get_applications",
        "ok_roles": ["adm1", "super"],
        "wrong_roles": ["adm2", "adm3"],
    },
    {
        "id": "adm2_review_queue",
        "method": "get",
        "path": "/api/adm2_get_approved",
        "ok_roles": ["adm2", "super"],
        "wrong_roles": ["adm1", "adm3"],
    },
    {
        "id": "dual_channel_shp_list",
        "method": "get",
        "path": "/api/adm1_get_shp_applications",
        "ok_roles": ALL_ADMINS,
        "wrong_roles": [],
    },
    {
        "id": "dual_channel_raster_list",
        "method": "get",
        "path": "/api/adm1_get_raster_applications",
        "ok_roles": ALL_ADMINS,
        "wrong_roles": [],
    },
    {
        "id": "all_applications",
        "method": "get",
        "path": "/api/applications",
        "ok_roles": ALL_ADMINS,
        "wrong_roles": [],
    },
    {
        "id": "promotion_application_detail",
        "method": "get",
        "path": "/api/admin-application/{admin_application_id}",
        "ok_roles": ALL_ADMINS,
        "wrong_roles": [],
    },
    {
        "id": "recall_list",
        "method": "get",
        "path": "/api/recall/list",
        "ok_roles": ALL_ADMINS,
        "wrong_roles": [],
    },
    {
        "id": "recall_detail",
        "method": "get",
        "path": "/api/recall/{recall_id}",
        "ok_roles": ALL_ADMINS,
        "wrong_roles": [],
    },
    {
        "id": "recall_history",
        "method": "get",
        "path": "/api/recall/history/{application_id}",
        "ok_roles": ALL_ADMINS,
        "wrong_roles": [],
    },
    {
        "id": "batch_review_failed_export",
        "method": "post",
        "path": "/api/admin/batch_review_failed_export",
        "json": {"failed": [{"id": 1, "reason": "示例原因", "msg": "示例消息"}]},
        "ok_roles": ALL_ADMINS,
        "wrong_roles": [],
    },
    {
        "id": "employee_details",
        "method": "get",
        "path": "/api/employee/details/E001",
        "ok_roles": ALL_ADMINS,
        "wrong_roles": [],
    },
]

ALLOWED_CASES = [
    pytest.param(spec, role, id=f"{spec['id']}-{role}") for spec in ENDPOINT_SPECS for role in spec["ok_roles"]
]

WRONG_SUB_ROLE_CASES = [
    pytest.param(spec, role, id=f"{spec['id']}-{role}") for spec in ENDPOINT_SPECS for role in spec["wrong_roles"]
]


def _spec_id(spec):
    return spec["id"]


def _request(client, spec, path, headers=None):
    if spec["method"] == "get":
        return client.get(path, headers=headers)
    return client.post(path, json=spec.get("json"), headers=headers)


@pytest.fixture
def authz_targets(db):
    """Seed one application, one promotion application and one recall proposal
    so the detail endpoints answer 200 instead of 404 for allowed roles."""
    from model.AdminApplication import AdminApplication
    from model.Application import Application
    from model.RecallProposal import RecallProposal

    application = Application(
        data_id=1,
        data_name="authz-review-app",
        data_alias="authz-review-app",
        data_type="vector",
        applicant_name="员工1",
        applicant_user_number="E001",
        reason="authz review seeding",
        adm1_statu=True,
        adm2_statu=True,
        # Keep this row outside every dashboard aggregation window: dashboard
        # ``_batch_day_counts`` casts the timestamp to DATE, which SQLite
        # returns as an int and the Date result processor rejects — a recent
        # row committed here would 500 the later test_dashboard.py tests.
        application_submission_time=datetime.now(UTC) - timedelta(days=30),
    )
    db.session.add(application)
    db.session.flush()

    promotion = AdminApplication(
        employee_number="E001",
        employee_name="员工1",
        reason="authz review promotion seeding reason",
        status="pending",
    )
    db.session.add(promotion)
    db.session.flush()

    proposal = RecallProposal(
        application_id=application.id,
        proposer_number="admin1",
        proposer_name="管理员1",
        proposer_role="adm1",
        reason="authz review recall seeding",
        status="voting",
        voting_deadline=datetime.now(UTC) + timedelta(days=3),
    )
    db.session.add(proposal)
    db.session.commit()

    return {
        "application_id": application.id,
        "admin_application_id": promotion.id,
        "recall_id": proposal.id,
    }


@pytest.fixture
def superadmin_headers(client, db):
    """Log in as a role='admin' super admin (must pass every gate)."""
    from werkzeug.security import generate_password_hash

    from model.Adm_Account import AdmAccount
    from model.Adm_Info import AdmInfo

    if not AdmAccount.query.filter_by(adm_user_name="superadmin").first():
        db.session.add(
            AdmInfo(
                adm_number="S001",
                name="超级管理员",
                job_number="ADMSUP",
                id_number="IDSUP",
                phone_number="13800000009",
                address="Test Address",
            )
        )
        db.session.flush()
        db.session.add(
            AdmAccount(
                adm_user_name="superadmin",
                adm_user_password=generate_password_hash("super123"),
                role="admin",
                adm_number="S001",
            )
        )
        db.session.commit()

    resp = client.post("/api/login", json={"username": "superadmin", "password": "super123", "role": "admin"})
    assert resp.status_code == 200, resp.get_data(as_text=True)
    return {"Authorization": f"Bearer {resp.get_json()['access_token']}"}


def _path(spec, targets):
    return spec["path"].format(**targets)


class TestReviewReadEndpoints:
    @pytest.mark.parametrize("spec", ENDPOINT_SPECS, ids=_spec_id)
    def test_no_token_returns_401(self, client, spec, authz_targets):
        resp = _request(client, spec, _path(spec, authz_targets))
        assert resp.status_code == 401, resp.get_data(as_text=True)

    @pytest.mark.parametrize("spec", ENDPOINT_SPECS, ids=_spec_id)
    def test_employee_forbidden_403(self, client, db, employee_headers, spec, authz_targets):
        resp = _request(client, spec, _path(spec, authz_targets), employee_headers)
        assert resp.status_code == 403, resp.get_data(as_text=True)

    @pytest.mark.parametrize("spec,role", ALLOWED_CASES)
    def test_allowed_role_can_read_200(self, client, db, request, authz_targets, spec, role):
        headers = request.getfixturevalue(ADMIN_ROLE_TO_FIXTURE[role])
        resp = _request(client, spec, _path(spec, authz_targets), headers)
        assert resp.status_code == 200, resp.get_data(as_text=True)

    @pytest.mark.parametrize("spec,role", WRONG_SUB_ROLE_CASES)
    def test_wrong_admin_sub_role_forbidden_403(self, client, db, request, authz_targets, spec, role):
        headers = request.getfixturevalue(ADMIN_ROLE_TO_FIXTURE[role])
        resp = _request(client, spec, _path(spec, authz_targets), headers)
        assert resp.status_code == 403, resp.get_data(as_text=True)


EMPLOYEE_ENDPOINTS_UNTOUCHED = [
    pytest.param("/api/get_applications", id="my_applications"),
    pytest.param("/api/get_approved_applications", id="my_approved_applications"),
    pytest.param("/api/employee/notifications", id="my_notifications"),
    pytest.param("/api/announcements", id="announcements"),
    pytest.param("/api/employee/profile", id="my_profile"),
    pytest.param("/api/applications/{application_id}", id="my_application_detail"),
]


class TestEmployeeEndpointsUntouched:
    """The tightening must not break endpoints that serve the employee's own
    data (their applications, notifications, announcements, profile)."""

    @pytest.mark.parametrize("path", EMPLOYEE_ENDPOINTS_UNTOUCHED)
    def test_employee_still_allowed(self, client, db, employee_headers, authz_targets, path):
        resp = client.get(path.format(**authz_targets), headers=employee_headers)
        assert resp.status_code == 200, resp.get_data(as_text=True)
