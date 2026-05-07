"""Tests for collaboration endpoints (notifications, chat, logs)."""


class TestNotifications:
    def test_requires_auth(self, client):
        resp = client.get('/api/employee/notifications')
        assert resp.status_code in (401, 422)

    def test_get_notifications(self, client, employee_headers):
        resp = client.get('/api/employee/notifications', headers=employee_headers)
        assert resp.status_code == 200

    def test_mark_read_requires_auth(self, client):
        resp = client.put('/api/employee/notifications/1/read')
        assert resp.status_code in (401, 422)


class TestMyLogs:
    def test_requires_auth(self, client):
        resp = client.get('/api/employee/my_logs')
        assert resp.status_code in (401, 422)

    def test_get_my_logs(self, client, employee_headers):
        resp = client.get('/api/employee/my_logs', headers=employee_headers)
        assert resp.status_code == 200


class TestChat:
    def test_conversations_requires_auth(self, client):
        resp = client.get('/api/chat/conversations')
        assert resp.status_code in (401, 422)

    def test_get_conversations(self, client, employee_headers):
        resp = client.get('/api/chat/conversations', headers=employee_headers)
        assert resp.status_code == 200

    def test_messages_requires_auth(self, client):
        resp = client.get('/api/chat/messages')
        assert resp.status_code in (401, 422)

    def test_send_requires_auth(self, client):
        resp = client.post('/api/chat/send', json={'content': 'hi'})
        assert resp.status_code in (401, 422)

    def test_search_users_requires_auth(self, client):
        resp = client.get('/api/chat/search_users?q=test')
        assert resp.status_code in (401, 422)

    def test_friend_requests_requires_auth(self, client):
        resp = client.get('/api/chat/friend_requests')
        assert resp.status_code in (401, 422)
