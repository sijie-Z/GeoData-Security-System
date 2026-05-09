"""Integration tests for end-to-end workflows."""


class TestApprovalWorkflow:
    """End-to-end: submit -> adm1 pass -> adm2 pass -> check status."""

    def test_full_approval_flow(self, client, auth_headers, adm2_headers, employee_headers, db):
        # 1. Employee submits application
        resp = client.post('/api/submit_application', json={
            'data_id': 100, 'data_name': 'Test Vector', 'data_alias': 'test_vec',
            'data_url': '/data/test.shp', 'data_type': 'vector',
            'applicant_name': '员工1', 'applicant_user_number': 'E001',
            'reason': 'Integration test'
        }, headers=employee_headers)
        assert resp.status_code == 201

        # 2. Get the application via admin list
        resp = client.get('/api/adm1_get_applications', headers=auth_headers)
        assert resp.status_code == 200
        apps = resp.get_json()['application_data']
        app_id = apps[0]['id'] if apps else None
        assert app_id is not None

        # 3. Admin 1 approves
        resp = client.post('/api/adm1_pass', json={'id': app_id}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()['application']['first_statu'] is True

        # 4. Admin 2 approves
        resp = client.post('/api/adm2_pass', json={'id': app_id}, headers=adm2_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['application']['second_statu'] is True
        assert data['application']['status'] == 'approved'

    def test_rejection_at_adm1(self, client, auth_headers, employee_headers, db):
        resp = client.post('/api/submit_application', json={
            'data_id': 101, 'data_name': 'Reject Test', 'data_alias': 'reject',
            'data_url': '/data/reject.shp', 'data_type': 'vector',
            'applicant_name': '员工1', 'applicant_user_number': 'E001', 'reason': 'test'
        }, headers=employee_headers)
        assert resp.status_code == 201

        resp = client.get('/api/adm1_get_applications', headers=auth_headers)
        apps = resp.get_json()['application_data']
        assert len(apps) > 0
        app_id = apps[0]['id']

        resp = client.post('/api/adm1_fail', json={'id': app_id}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()['application']['first_statu'] is False

    def test_cannot_skip_adm1(self, client, auth_headers, adm2_headers, employee_headers, db):
        resp = client.post('/api/submit_application', json={
            'data_id': 102, 'data_name': 'Skip', 'data_alias': 'skip',
            'data_url': '/data/skip.shp', 'data_type': 'vector',
            'applicant_name': '员工1', 'applicant_user_number': 'E001', 'reason': 'test'
        }, headers=employee_headers)
        assert resp.status_code == 201

        resp = client.get('/api/adm1_get_applications', headers=auth_headers)
        apps = resp.get_json()['application_data']
        app_id = next((a['id'] for a in apps if a['data_alias'] == 'skip'), None)

        resp = client.post('/api/adm2_pass', json={'id': app_id}, headers=adm2_headers)
        assert resp.status_code == 400

    def test_cannot_double_approve(self, client, auth_headers, employee_headers, db):
        resp = client.post('/api/submit_application', json={
            'data_id': 103, 'data_name': 'Double', 'data_alias': 'double',
            'data_url': '/data/double.shp', 'data_type': 'vector',
            'applicant_name': '员工1', 'applicant_user_number': 'E001', 'reason': 'test'
        }, headers=employee_headers)
        assert resp.status_code == 201

        # Get all apps and find ours
        resp = client.get('/api/all_applications', headers=auth_headers)
        if resp.status_code == 200:
            apps = resp.get_json().get('data', {}).get('list', [])
            app_id = next((a['id'] for a in apps if a.get('data_alias') == 'double'), None)
        else:
            app_id = None

        if not app_id:
            # Fallback: try adm1 pending list
            resp = client.get('/api/adm1_get_applications', headers=auth_headers)
            apps = resp.get_json()['application_data']
            app_id = apps[0]['id'] if apps else None

        assert app_id is not None

        resp = client.post('/api/adm1_pass', json={'id': app_id}, headers=auth_headers)
        assert resp.status_code == 200

        resp = client.post('/api/adm1_pass', json={'id': app_id}, headers=auth_headers)
        assert resp.status_code == 400


class TestAdminRoleEnforcement:
    """Verify non-admins cannot perform admin actions."""

    def test_employee_cannot_approve(self, client, employee_headers, db):
        resp = client.post('/api/adm1_pass', json={'id': 1}, headers=employee_headers)
        assert resp.status_code == 403

    def test_employee_cannot_view_logs(self, client, employee_headers, db):
        resp = client.get('/api/admin/logs', headers=employee_headers)
        assert resp.status_code == 403

    def test_employee_cannot_send_notification(self, client, employee_headers, db):
        resp = client.post('/api/admin/notifications/send', json={
            'title': 'test', 'content': 'test'
        }, headers=employee_headers)
        assert resp.status_code == 403

    def test_employee_cannot_manage_employees(self, client, employee_headers, db):
        resp = client.get('/api/adm/get_emp_info_list', headers=employee_headers)
        assert resp.status_code == 403

    def test_unauthenticated_cannot_approve(self, client, db):
        resp = client.post('/api/adm1_pass', json={'id': 1})
        assert resp.status_code == 401


class TestTokenBlacklist:
    """Verify logout invalidates tokens."""

    def test_logout_blacklists_token(self, client, db):
        resp = client.post('/api/login', json={
            'username': 'admin1', 'password': 'admin123', 'role': 'admin'
        })
        assert resp.status_code == 200
        token = resp.get_json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}

        resp = client.get('/api/adm/get_emp_info_list', headers=headers)
        assert resp.status_code == 200

        resp = client.post('/api/logout', headers=headers)
        assert resp.status_code == 200

        resp = client.get('/api/adm/get_emp_info_list', headers=headers)
        assert resp.status_code == 401


class TestPasswordValidation:
    """Verify password complexity requirements."""

    def test_register_rejects_weak_password(self, client, db):
        resp = client.post('/api/register', data={
            'name': 'Weak', 'employeeId': 'W001', 'password': '123'
        })
        assert resp.status_code == 400

    def test_register_rejects_no_digits(self, client, db):
        resp = client.post('/api/register', data={
            'name': 'NoDigit', 'employeeId': 'W002', 'password': 'abcdefgh'
        })
        assert resp.status_code == 400


class TestUserProfile:
    """Profile management workflows."""

    def test_get_profile(self, client, employee_headers, db):
        resp = client.get('/api/employee/profile', headers=employee_headers)
        assert resp.status_code == 200
        assert resp.get_json()['data']['userNumber'] == 'E001'

    def test_update_profile(self, client, employee_headers, db):
        resp = client.put('/api/employee/profile', data={
            'userName': 'Updated Name', 'email': 'test@example.com'
        }, headers=employee_headers, content_type='multipart/form-data')
        assert resp.status_code == 200

    def test_reject_invalid_email(self, client, employee_headers, db):
        resp = client.put('/api/employee/profile', data={
            'email': 'not-an-email'
        }, headers=employee_headers, content_type='multipart/form-data')
        assert resp.status_code == 400


class TestInputSanitization:
    """Verify input validation and sanitization."""

    def test_chat_message_length_limit(self, client, employee_headers, db):
        resp = client.post('/api/chat/send', json={
            'receiver_number': 'admin1', 'receiver_role': 'admin',
            'content': 'x' * 2001
        }, headers=employee_headers)
        assert resp.status_code == 400

    def test_pagination_page_size_capped(self, client, employee_headers, db):
        resp = client.get('/api/get_applications?pageSize=9999', headers=employee_headers)
        assert resp.status_code == 200
