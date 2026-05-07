"""Tests for dashboard endpoints."""


class TestAdminDashboard:
    def test_requires_auth(self, client):
        resp = client.get('/api/admin/dashboard')
        assert resp.status_code in (401, 422)

    def test_requires_admin_role(self, client, employee_headers):
        resp = client.get('/api/admin/dashboard', headers=employee_headers)
        assert resp.status_code == 403

    def test_admin_dashboard_success(self, client, auth_headers):
        resp = client.get('/api/admin/dashboard', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] is True
        assert 'data' in data
        d = data['data']
        assert 'total_users' in d
        assert 'total_admins' in d
        assert 'pending_applications' in d
        assert 'today' in d
        assert 'daily_trend' in d
        assert 'alerts' in d
        assert 'status_distribution' in d


class TestEmployeeDashboard:
    def test_requires_auth(self, client):
        resp = client.get('/api/employee/dashboard')
        assert resp.status_code in (401, 422)

    def test_employee_dashboard_success(self, client, employee_headers):
        resp = client.get('/api/employee/dashboard', headers=employee_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] is True
        assert 'data' in data
        d = data['data']
        assert 'total_applications' in d
        assert 'pending_applications' in d
        assert 'recent_applications' in d
        assert 'daily_trend' in d
