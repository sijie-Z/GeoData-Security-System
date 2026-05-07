"""Tests for employee management endpoints."""


class TestEmployeeManagement:
    def test_get_employee_list_requires_auth(self, client):
        resp = client.get('/api/adm/get_emp_info_list')
        assert resp.status_code in (401, 422)

    def test_get_employee_list(self, client, auth_headers):
        resp = client.get('/api/adm/get_emp_info_list', headers=auth_headers)
        assert resp.status_code == 200

    def test_add_employee_requires_auth(self, client):
        resp = client.post('/api/adm/add_employee', json={'name': 'test'})
        assert resp.status_code in (401, 422)

    def test_add_employee_missing_fields(self, client, auth_headers):
        resp = client.post('/api/adm/add_employee', headers=auth_headers, json={})
        assert resp.status_code in (400, 422, 500)

    def test_create_account_requires_auth(self, client):
        resp = client.post('/api/account/create', json={'username': 'test'})
        assert resp.status_code in (401, 422)

    def test_employee_details_requires_auth(self, client):
        resp = client.get('/api/employee/details/E001')
        assert resp.status_code in (401, 422)

    def test_employee_update_requires_auth(self, client):
        resp = client.put('/api/employee/E001', json={'name': 'test'})
        assert resp.status_code in (401, 422)

    def test_delete_employee_requires_auth(self, client):
        resp = client.delete('/api/admin/employee/E001')
        assert resp.status_code in (401, 422)

    def test_nonexistent_employee(self, client, auth_headers):
        resp = client.get('/api/employee/details/NONEXISTENT', headers=auth_headers)
        assert resp.status_code in (404, 200)
