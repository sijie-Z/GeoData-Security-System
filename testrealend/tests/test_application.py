import pytest


class TestApplicationSubmission:
    """Tests for application submission."""

    def test_submit_requires_auth(self, client):
        response = client.post(
            "/api/submit_application",
            json={
                "data_id": 1,
                "data_name": "Test Data",
                "data_alias": "test",
                "applicant_name": "Test User",
                "applicant_user_number": "12345",
            },
        )
        assert response.status_code == 401

    def test_submit_missing_required_fields(self, client, auth_headers):
        if not auth_headers:
            pytest.skip("No auth headers available")
        response = client.post("/api/submit_application", json={}, headers=auth_headers)
        # Should fail due to missing fields
        assert response.status_code in [400, 500]

    @pytest.mark.parametrize(
        "bad_id",
        [float("inf"), float("-inf"), 10**30, 2**63, "abc", "1/../../etc", None],
        ids=["inf", "-inf", "huge-int", "int64-overflow", "non-numeric", "path-separator", "none"],
    )
    def test_submit_rejects_non_integer_data_id(self, client, db, employee_headers, bad_id):
        """JSON Infinity / oversized integers are client errors, not 500s.

        ``int(float('inf'))`` raises OverflowError and a 400-character JSON
        integer would overflow the DB driver's 64-bit bind; both must answer
        400 without touching any dataset lookup.
        """
        response = client.post(
            "/api/submit_application",
            json={"data_id": bad_id, "data_alias": "bad-id", "data_type": "vector"},
            headers=employee_headers,
        )
        assert response.status_code == 400, response.get_data(as_text=True)
        assert response.get_json()["msg"] == "数据不存在"


class TestApplicationApproval:
    """Tests for application approval workflow."""

    def test_approve_requires_auth(self, client):
        response = client.post("/api/adm1_pass", json={"id": 1})
        assert response.status_code == 401

    def test_approve_nonexistent_application(self, client, auth_headers):
        if not auth_headers:
            pytest.skip("No auth headers available")
        response = client.post("/api/adm1_pass", json={"id": 999999}, headers=auth_headers)
        assert response.status_code == 404
