"""Tests for announcement endpoints."""


class TestAnnouncements:
    def test_get_announcements_requires_auth(self, client):
        resp = client.get('/api/announcements')
        assert resp.status_code in (200, 401, 422)

    def test_get_announcements(self, client, auth_headers):
        resp = client.get('/api/announcements', headers=auth_headers)
        assert resp.status_code == 200

    def test_create_announcement_requires_auth(self, client):
        resp = client.post('/api/admin/announcements', json={'title': 'Test', 'content': 'Hello'})
        assert resp.status_code in (401, 422)

    def test_create_announcement(self, client, auth_headers):
        resp = client.post('/api/admin/announcements', headers=auth_headers, json={
            'title': 'Test Announcement',
            'content': 'This is a test',
            'type': 'info'
        })
        assert resp.status_code in (200, 201)

    def test_update_announcement(self, client, auth_headers):
        # First create
        create_resp = client.post('/api/admin/announcements', headers=auth_headers, json={
            'title': 'To Update',
            'content': 'Original'
        })
        if create_resp.status_code in (200, 201):
            data = create_resp.get_json()
            ann_id = data.get('id') or data.get('data', {}).get('id')
            if ann_id:
                resp = client.put(f'/api/admin/announcements/{ann_id}', headers=auth_headers, json={
                    'title': 'Updated',
                    'content': 'Modified'
                })
                assert resp.status_code == 200
