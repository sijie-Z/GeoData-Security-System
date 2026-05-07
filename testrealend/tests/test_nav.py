"""Tests for navigation endpoints."""


class TestNavigation:
    def test_admin_nav_tree_requires_auth(self, client):
        resp = client.get('/api/admin/nav/tree')
        assert resp.status_code in (401, 422)

    def test_admin_nav_tree(self, client, auth_headers):
        resp = client.get('/api/admin/nav/tree', headers=auth_headers)
        assert resp.status_code == 200

    def test_employee_nav_tree_requires_auth(self, client):
        resp = client.get('/api/employee/nav/tree')
        assert resp.status_code in (401, 422)

    def test_employee_nav_tree(self, client, employee_headers):
        resp = client.get('/api/employee/nav/tree', headers=employee_headers)
        assert resp.status_code == 200

    def test_admin_nav_list(self, client, auth_headers):
        resp = client.get('/api/admin/nav/list', headers=auth_headers)
        assert resp.status_code == 200

    def test_employee_nav_list(self, client, employee_headers):
        resp = client.get('/api/employee/nav/list', headers=employee_headers)
        assert resp.status_code == 200
