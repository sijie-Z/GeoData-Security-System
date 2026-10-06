"""Tests for collaboration endpoints (notifications, chat, logs)."""


class TestNotifications:
    def test_requires_auth(self, client):
        resp = client.get("/api/employee/notifications")
        assert resp.status_code in (401, 422)

    def test_get_notifications(self, client, employee_headers):
        resp = client.get("/api/employee/notifications", headers=employee_headers)
        assert resp.status_code == 200

    def test_mark_read_requires_auth(self, client):
        resp = client.put("/api/employee/notifications/1/read")
        assert resp.status_code in (401, 405, 422)


class TestMyLogs:
    def test_requires_auth(self, client):
        resp = client.get("/api/employee/my_logs")
        assert resp.status_code in (401, 422)

    def test_get_my_logs(self, client, employee_headers):
        resp = client.get("/api/employee/my_logs", headers=employee_headers)
        assert resp.status_code == 200


class TestChat:
    def test_conversations_requires_auth(self, client):
        resp = client.get("/api/chat/conversations")
        assert resp.status_code in (401, 422)

    def test_get_conversations(self, client, employee_headers):
        resp = client.get("/api/chat/conversations", headers=employee_headers)
        assert resp.status_code == 200

    def test_messages_requires_auth(self, client):
        resp = client.get("/api/chat/messages")
        assert resp.status_code in (401, 422)

    def test_send_requires_auth(self, client):
        resp = client.post("/api/chat/send", json={"content": "hi"})
        assert resp.status_code in (401, 422)

    def test_search_users_requires_auth(self, client):
        resp = client.get("/api/chat/search_users?q=test")
        assert resp.status_code in (401, 422)

    def test_friend_requests_requires_auth(self, client):
        resp = client.get("/api/chat/friend_requests")
        assert resp.status_code in (401, 422)


class TestChatRoleVocabulary:
    """Regression (API campaign domain08): /api/chat/search_users advertises
    admins with role 'admin' while the admin JWT carries the sub-role
    ('admin1'), and conversations/messages/mark_read/friend queries matched
    roles exactly — messages the employee sent with the advertised value were
    stored but invisible to the admin (collaboration_resource.py:241-247 vs
    :376-382). Roles must be matched admin-family-wide and normalised to the
    canonical 'admin' on writes and outputs."""

    def test_employee_message_with_directory_role_is_visible(self, client, employee_headers, auth_headers):
        send = client.post(
            "/api/chat/send",
            headers=employee_headers,
            json={"receiver_number": "admin1", "receiver_role": "admin", "content": "hello-admin-canonical"},
        )
        assert send.status_code == 200, send.get_data(as_text=True)

        conv = client.get("/api/chat/conversations", headers=auth_headers)
        assert conv.status_code == 200
        peer = next((c for c in conv.get_json()["data"] if c["peer_number"] == "E001"), None)
        assert peer is not None, conv.get_json()
        assert peer["last_message"] == "hello-admin-canonical"
        assert peer["unread_count"] >= 1

        msgs = client.get(
            "/api/chat/messages",
            headers=auth_headers,
            query_string={"peer_number": "E001", "peer_role": "employee"},
        )
        assert msgs.status_code == 200
        assert any(m["content"] == "hello-admin-canonical" for m in msgs.get_json()["data"])

        mark = client.post(
            "/api/chat/mark_read",
            headers=auth_headers,
            json={"peer_number": "E001", "peer_role": "employee"},
        )
        assert mark.status_code == 200
        conv2 = client.get("/api/chat/conversations", headers=auth_headers)
        peer2 = next((c for c in conv2.get_json()["data"] if c["peer_number"] == "E001"), None)
        assert peer2 is not None and peer2["unread_count"] == 0

        # The employee side sees the admin under the canonical role.
        econv = client.get("/api/chat/conversations", headers=employee_headers)
        epeer = next((c for c in econv.get_json()["data"] if c["peer_number"] == "admin1"), None)
        assert epeer is not None
        assert epeer["peer_role"] == "admin"

    def test_legacy_admin_subrole_rows_stay_visible(self, client, db, employee_headers, auth_headers):
        from model.ChatMessage import ChatMessage

        db.session.add(
            ChatMessage(
                sender_number="admin1",
                sender_role="admin1",
                receiver_number="E001",
                receiver_role="employee",
                content="legacy-subrole-row",
            )
        )
        db.session.commit()

        msgs = client.get(
            "/api/chat/messages",
            headers=auth_headers,
            query_string={"peer_number": "E001", "peer_role": "employee"},
        )
        assert msgs.status_code == 200
        assert any(m["content"] == "legacy-subrole-row" for m in msgs.get_json()["data"])

    def test_send_normalises_roles_on_write(self, client, db, employee_headers, auth_headers):
        from model.ChatMessage import ChatMessage

        send = client.post(
            "/api/chat/send",
            headers=auth_headers,
            json={"receiver_number": "E001", "receiver_role": "employee", "content": "canonical-write"},
        )
        assert send.status_code == 200
        row = ChatMessage.query.filter_by(content="canonical-write").first()
        assert row is not None
        assert row.sender_role == "admin"  # canonical, not the JWT sub-role "admin1"
        assert row.receiver_role == "employee"

    def test_friend_request_with_directory_role_reaches_admin(self, client, employee_headers, auth_headers):
        add = client.post(
            "/api/chat/add_friend",
            headers=employee_headers,
            json={"friend_number": "admin1", "friend_role": "admin"},
        )
        assert add.status_code == 200, add.get_data(as_text=True)

        reqs = client.get("/api/chat/friend_requests", headers=auth_headers)
        assert reqs.status_code == 200
        req = next((r for r in reqs.get_json()["data"] if r["owner_number"] == "E001"), None)
        assert req is not None, reqs.get_json()

        respond = client.post(
            "/api/chat/friend_respond",
            headers=auth_headers,
            json={"request_id": req["id"], "action": "accept"},
        )
        assert respond.status_code == 200

        again = client.post(
            "/api/chat/friend_respond",
            headers=auth_headers,
            json={"request_id": req["id"], "action": "accept"},
        )
        assert again.status_code == 404
