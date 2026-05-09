

class TestLogin:
    """Tests for the login endpoint."""

    def test_login_missing_fields(self, client):
        response = client.post('/api/login', json={})
        assert response.status_code == 401

    def test_login_wrong_credentials(self, client):
        response = client.post('/api/login', json={
            'username': 'nonexistent',
            'password': 'wrongpassword',
            'role': 'employee'
        })
        assert response.status_code == 401
        data = response.get_json()
        assert data['status'] is False

    def test_login_empty_password(self, client):
        response = client.post('/api/login', json={
            'username': 'testuser',
            'password': '',
            'role': 'employee'
        })
        assert response.status_code == 401


class TestRegister:
    """Tests for the registration endpoint."""

    def test_register_missing_fields(self, client):
        response = client.post('/api/register', json={})
        assert response.status_code in (400, 401, 422, 500)

    def test_register_duplicate_employee_id(self, client):
        # This would require setting up test data first
        pass


class TestTokenRefresh:
    """Tests for token refresh."""

    def test_refresh_without_token(self, client):
        response = client.post('/api/refresh-token', json={})
        assert response.status_code == 401

    def test_refresh_with_invalid_token(self, client):
        response = client.post('/api/refresh-token', json={
            'refresh_token': 'invalid-token'
        })
        assert response.status_code == 401
