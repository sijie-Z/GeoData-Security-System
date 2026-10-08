"""AI_TIMEOUT steers the chat / chat-stream HTTP timeouts (env-driven, per request).

The default (120s) must cover a local model's cold start; a small configured
value must cut a stalled provider call short. Hermetic: the provider is a local
stdlib ``http.server`` mock bound to 127.0.0.1 on a random port — no test
touches the outside network.
"""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from utils.ai_config import DEFAULT_AI_TIMEOUT, _get_ai_timeout

MOCK_KEY = "test-ai-timeout-key"
MOCK_MODEL = "mock-timeout-model"
MOCK_REPLY = "超时配置冒烟回复"

# The mock stalls before answering. Timeout tests stall well beyond the tiny
# configured timeout yet far below the 120s default, so a 502 can only mean the
# configured value (not the default) cut the call.
TINY_TIMEOUT = 0.5
STALL_OVER_TINY = 3.0
STALL_UNDER_DEFAULT = 1.5

# Environment variables that steer the AI endpoint; cleared before every test
# so an ambient value in the developer shell can never leak into a test run.
_AI_ENV_VARS = ("AI_API_BASE", "AI_MODEL", "AI_API_KEY", "DEEPSEEK_API_KEY", "AI_TIMEOUT")


class _StallingMockAIHandler(BaseHTTPRequestHandler):
    """Stalls ``server.stall`` seconds, then replies with a chat / SSE body."""

    def do_POST(self):  # stdlib naming convention
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        self.server.requests.append({"path": self.path, "body": body})
        time.sleep(self.server.stall)
        if body.get("stream"):
            payload = (
                b'data: {"choices":[{"delta":{"content":"MockToken1"}}]}\n\n'
                b'data: {"choices":[{"delta":{"content":"MockToken2"}}]}\n\n'
                b"data: [DONE]\n\n"
            )
            content_type = "text/event-stream"
        else:
            payload = json.dumps({"choices": [{"message": {"role": "assistant", "content": MOCK_REPLY}}]}).encode(
                "utf-8"
            )
            content_type = "application/json"
        try:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass  # timeout tests close the socket while this handler is still stalled

    def log_message(self, format, *args):  # keep stderr quiet
        pass


class _QuietThreadingHTTPServer(ThreadingHTTPServer):
    """ThreadingHTTPServer that stays quiet when a stalled write hits a closed socket."""

    daemon_threads = True

    def handle_error(self, request, client_address):
        pass


@pytest.fixture(autouse=True)
def _hermetic_ai_env(monkeypatch):
    """Drop ambient AI env vars so tests never talk to a real provider."""
    for name in _AI_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture()
def mock_ai_server():
    """Local slow OpenAI-compatible mock on a random 127.0.0.1 port."""
    server = _QuietThreadingHTTPServer(("127.0.0.1", 0), _StallingMockAIHandler)
    server.requests = []
    server.stall = 0.0
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _point_at_mock(monkeypatch, server):
    monkeypatch.setenv("AI_API_BASE", f"http://127.0.0.1:{server.server_address[1]}")
    monkeypatch.setenv("AI_MODEL", MOCK_MODEL)
    monkeypatch.setenv("AI_API_KEY", MOCK_KEY)


# ── AI_TIMEOUT 解析：默认 / 合法值 / 非法值回落 ──


def test_timeout_default_when_unset():
    assert _get_ai_timeout() == DEFAULT_AI_TIMEOUT == 120.0


@pytest.mark.parametrize("raw", ["", "  ", "abc", "12s", "0", "-3", "0.0", "nan", "inf", "-inf"])
def test_timeout_invalid_values_fall_back_to_default(monkeypatch, raw):
    monkeypatch.setenv("AI_TIMEOUT", raw)
    assert _get_ai_timeout() == DEFAULT_AI_TIMEOUT


def test_timeout_valid_value_is_honoured(monkeypatch):
    monkeypatch.setenv("AI_TIMEOUT", "0.5")
    assert _get_ai_timeout() == 0.5
    monkeypatch.setenv("AI_TIMEOUT", "45")
    assert _get_ai_timeout() == 45.0


# ── 端点行为：配置了小值 → 慢端点被切断；默认 → 慢响应照常通过 ──


def test_chat_times_out_when_stall_exceeds_configured_timeout(client, auth_headers, mock_ai_server, monkeypatch):
    _point_at_mock(monkeypatch, mock_ai_server)
    monkeypatch.setenv("AI_TIMEOUT", str(TINY_TIMEOUT))
    mock_ai_server.stall = STALL_OVER_TINY

    resp = client.post("/api/ai/chat", json={"message": "ping"}, headers=auth_headers)

    assert resp.status_code == 502
    assert "timed out" in resp.get_json()["msg"]
    assert len(mock_ai_server.requests) == 1  # the request did reach the (stalled) provider


def test_chat_allows_slow_reply_under_default_timeout(client, auth_headers, mock_ai_server, monkeypatch):
    _point_at_mock(monkeypatch, mock_ai_server)
    mock_ai_server.stall = STALL_UNDER_DEFAULT  # AI_TIMEOUT unset → default 120s

    resp = client.post("/api/ai/chat", json={"message": "ping"}, headers=auth_headers)

    assert resp.status_code == 200
    assert resp.get_json()["data"]["reply"] == MOCK_REPLY


def test_stream_times_out_when_stall_exceeds_configured_timeout(client, auth_headers, mock_ai_server, monkeypatch):
    _point_at_mock(monkeypatch, mock_ai_server)
    monkeypatch.setenv("AI_TIMEOUT", str(TINY_TIMEOUT))
    mock_ai_server.stall = STALL_OVER_TINY

    resp = client.post("/api/ai/chat/stream", json={"message": "ping"}, headers=auth_headers)

    # SSE headers are already flushed; the timeout surfaces as an error frame in the body.
    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert '"error"' in text
    assert "timed out" in text


def test_stream_allows_slow_reply_under_default_timeout(client, auth_headers, mock_ai_server, monkeypatch):
    _point_at_mock(monkeypatch, mock_ai_server)
    mock_ai_server.stall = STALL_UNDER_DEFAULT  # AI_TIMEOUT unset → default 120s

    resp = client.post("/api/ai/chat/stream", json={"message": "ping"}, headers=auth_headers)

    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert "MockToken1" in text
    assert "MockToken2" in text
    assert '"done": true' in text
