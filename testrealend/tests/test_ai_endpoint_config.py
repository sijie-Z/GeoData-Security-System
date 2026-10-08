"""Tests for the env-driven AI endpoint config (AI_API_BASE / AI_MODEL / AI_API_KEY).

Hermetic: every provider call is answered by a local stdlib ``http.server`` mock
bound to 127.0.0.1 on a random port — no test touches the outside network.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from resource.ai_chat_resource import (
    DEFAULT_AI_API_BASE,
    DEFAULT_AI_MODEL,
    _chat_completions_url,
    _get_ai_config,
)

MOCK_KEY = "test-ai-key-123"
MOCK_MODEL = "mock-model-v1"
MISSING_KEY_MSG = "AI 服务未配置（缺少 AI_API_KEY 环境变量）"

# Environment variables that steer the AI endpoint; cleared before every test
# so an ambient key in the developer shell can never leak into a test run.
_AI_ENV_VARS = ("AI_API_BASE", "AI_MODEL", "AI_API_KEY", "DEEPSEEK_API_KEY")


class _MockAIHandler(BaseHTTPRequestHandler):
    """Records each POST and replies with OpenAI-shaped chat / SSE bodies."""

    def do_POST(self):  # stdlib naming convention
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        self.server.requests.append(
            {
                "path": self.path,
                "authorization": self.headers.get("Authorization"),
                "content_type": self.headers.get("Content-Type"),
                "body": body,
            }
        )
        if body.get("stream"):
            payload = (
                b'data: {"choices":[{"delta":{"content":"MockToken1"}}]}\n\n'
                b'data: {"choices":[{"delta":{"content":"MockToken2"}}]}\n\n'
                b"data: [DONE]\n\n"
            )
            content_type = "text/event-stream"
        else:
            payload = json.dumps({"choices": [{"message": {"role": "assistant", "content": "mock-reply-ok"}}]}).encode(
                "utf-8"
            )
            content_type = "application/json"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):  # keep stderr quiet
        pass


@pytest.fixture(autouse=True)
def _hermetic_ai_env(monkeypatch):
    """Drop ambient AI env vars so tests never talk to a real provider."""
    for name in _AI_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture()
def mock_ai_server():
    """Local OpenAI-compatible mock on a random 127.0.0.1 port."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _MockAIHandler)
    server.requests = []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _mock_base_url(server):
    return f"http://127.0.0.1:{server.server_address[1]}"


# ── 未配置 → 503（契约新消息串） ──


def test_chat_without_key_returns_503_with_new_message(client, auth_headers):
    resp = client.post("/api/ai/chat", json={"message": "你好"}, headers=auth_headers)
    assert resp.status_code == 503
    assert resp.get_json()["msg"] == MISSING_KEY_MSG


def test_stream_without_key_returns_503_with_new_message(client, auth_headers):
    resp = client.post("/api/ai/chat/stream", json={"message": "你好"}, headers=auth_headers)
    assert resp.status_code == 503
    assert resp.get_json()["msg"] == MISSING_KEY_MSG


# ── 设齐 AI_API_* + 本地 mock → 全链路走通 ──


def test_chat_uses_configured_endpoint(client, auth_headers, mock_ai_server, monkeypatch):
    monkeypatch.setenv("AI_API_BASE", _mock_base_url(mock_ai_server))
    monkeypatch.setenv("AI_MODEL", MOCK_MODEL)
    monkeypatch.setenv("AI_API_KEY", MOCK_KEY)

    resp = client.post("/api/ai/chat", json={"message": "ping"}, headers=auth_headers)

    assert resp.status_code == 200
    assert resp.get_json()["data"]["reply"] == "mock-reply-ok"
    assert len(mock_ai_server.requests) == 1
    req = mock_ai_server.requests[0]
    assert req["path"] == "/chat/completions"
    assert req["authorization"] == f"Bearer {MOCK_KEY}"
    assert req["content_type"] == "application/json"
    assert req["body"]["model"] == MOCK_MODEL
    assert req["body"]["messages"][-1] == {"role": "user", "content": "ping"}


def test_stream_uses_configured_endpoint(client, auth_headers, mock_ai_server, monkeypatch):
    monkeypatch.setenv("AI_API_BASE", _mock_base_url(mock_ai_server))
    monkeypatch.setenv("AI_MODEL", MOCK_MODEL)
    monkeypatch.setenv("AI_API_KEY", MOCK_KEY)

    resp = client.post("/api/ai/chat/stream", json={"message": "ping"}, headers=auth_headers)

    assert resp.status_code == 200
    text = resp.get_data(as_text=True)
    assert "MockToken1" in text
    assert "MockToken2" in text
    assert '"done": true' in text
    assert len(mock_ai_server.requests) == 1
    req = mock_ai_server.requests[0]
    assert req["path"] == "/chat/completions"
    assert req["authorization"] == f"Bearer {MOCK_KEY}"
    assert req["body"]["model"] == MOCK_MODEL
    assert req["body"]["stream"] is True


# ── 仅设旧名 DEEPSEEK_API_KEY → 回落生效 ──


def test_legacy_deepseek_key_falls_back(client, auth_headers, mock_ai_server, monkeypatch):
    monkeypatch.setenv("AI_API_BASE", _mock_base_url(mock_ai_server))
    monkeypatch.setenv("DEEPSEEK_API_KEY", MOCK_KEY)  # AI_API_KEY intentionally unset

    resp = client.post("/api/ai/chat", json={"message": "ping"}, headers=auth_headers)

    assert resp.status_code == 200
    assert len(mock_ai_server.requests) == 1
    req = mock_ai_server.requests[0]
    assert req["authorization"] == f"Bearer {MOCK_KEY}"
    # AI_API_BASE 给了 mock，但 AI_MODEL 未设 → 默认模型
    assert req["body"]["model"] == DEFAULT_AI_MODEL


# ── 配置解析与 URL 拼装（默认域无法走 mock，做单元断言） ──


def test_defaults_when_unset(monkeypatch):
    api_base, api_key, model = _get_ai_config()
    assert api_base == DEFAULT_AI_API_BASE == "https://api.deepseek.com"
    assert api_key == ""
    assert model == DEFAULT_AI_MODEL == "deepseek-chat"

    # 空串视同未配置
    monkeypatch.setenv("AI_API_BASE", "")
    monkeypatch.setenv("AI_MODEL", "")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    api_base, api_key, model = _get_ai_config()
    assert (api_base, api_key, model) == ("https://api.deepseek.com", "", "deepseek-chat")


def test_api_key_takes_priority_over_legacy(monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "new-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "old-key")
    assert _get_ai_config()[1] == "new-key"


def test_chat_completions_url_construction():
    assert _chat_completions_url(DEFAULT_AI_API_BASE) == "https://api.deepseek.com/chat/completions"
    # 尾部斜杠归一化；本地 OpenAI 兼容基路径（如 Ollama 的 /v1）直接拼接
    assert _chat_completions_url("http://localhost:11434/v1/") == "http://localhost:11434/v1/chat/completions"
    assert _chat_completions_url("http://localhost:11434/v1") == "http://localhost:11434/v1/chat/completions"
