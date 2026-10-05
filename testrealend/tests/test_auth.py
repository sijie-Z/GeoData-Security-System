class TestLogin:
    """Tests for the login endpoint."""

    def test_login_missing_fields(self, client):
        response = client.post("/api/login", json={})
        assert response.status_code == 401

    def test_login_wrong_credentials(self, client):
        response = client.post(
            "/api/login", json={"username": "nonexistent", "password": "wrongpassword", "role": "employee"}
        )
        assert response.status_code == 401
        data = response.get_json()
        assert data["status"] is False

    def test_login_empty_password(self, client):
        response = client.post("/api/login", json={"username": "testuser", "password": "", "role": "employee"})
        assert response.status_code == 401


class TestRegister:
    """Tests for the registration endpoint."""

    @staticmethod
    def _unique_registration():
        import uuid

        suffix = uuid.uuid4().hex[:8]
        return {
            "name": "Reg Tester",
            "employeeId": f"reg_{suffix}",
            "idNumber": f"IDN-{suffix}",
            "phone": "139" + str(uuid.uuid4().int)[:8],
            "password": "Passw0rd1",
        }

    def test_register_missing_fields(self, client):
        response = client.post("/api/register", json={})
        assert response.status_code in (400, 401, 422, 500)

    def test_register_duplicate_employee_id(self, client):
        data = self._unique_registration()
        assert client.post("/api/register", data=data).status_code == 201
        dup = dict(data, idNumber="IDN-other-1", phone="13900000001")
        resp = client.post("/api/register", data=dup)
        assert resp.status_code == 400
        assert "员工编号" in resp.get_json()["msg"]

    def test_register_duplicate_id_number_returns_400_naming_field(self, client):
        """Regression (API campaign domain01): a duplicate id_number hit the
        DB unique index and leaked as a generic 500 (IntegrityError 1062)."""
        data = self._unique_registration()
        assert client.post("/api/register", data=data).status_code == 201
        dup = dict(data, employeeId=data["employeeId"] + "b", phone="13900000002")
        resp = client.post("/api/register", data=dup)
        assert resp.status_code == 400, resp.get_data(as_text=True)
        assert "身份证号" in resp.get_json()["msg"]

    def test_register_duplicate_phone_returns_400_naming_field(self, client):
        data = self._unique_registration()
        assert client.post("/api/register", data=data).status_code == 201
        dup = dict(data, employeeId=data["employeeId"] + "c", idNumber="IDN-other-2")
        resp = client.post("/api/register", data=dup)
        assert resp.status_code == 400, resp.get_data(as_text=True)
        assert "手机号" in resp.get_json()["msg"]

    def test_register_missing_id_number_returns_400(self, client):
        """Regression (API campaign domain01): id_number/phone are NOT NULL in
        the model while the docstring called them optional; a missing value
        leaked as a generic 500 (IntegrityError 1048)."""
        data = self._unique_registration()
        data.pop("idNumber")
        resp = client.post("/api/register", data=data)
        assert resp.status_code == 400, resp.get_data(as_text=True)
        assert "身份证号" in resp.get_json()["msg"]

    def test_register_missing_phone_returns_400(self, client):
        data = self._unique_registration()
        data.pop("phone")
        resp = client.post("/api/register", data=data)
        assert resp.status_code == 400, resp.get_data(as_text=True)
        assert "手机号" in resp.get_json()["msg"]


class TestTokenRefresh:
    """Tests for token refresh."""

    def test_refresh_without_token(self, client):
        response = client.post("/api/refresh-token", json={})
        assert response.status_code == 401

    def test_refresh_with_invalid_token(self, client):
        response = client.post("/api/refresh-token", json={"refresh_token": "invalid-token"})
        assert response.status_code == 401
