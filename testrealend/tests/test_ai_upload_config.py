"""Upload auto-description resolves its AI endpoint through utils.ai_config.

``_bg_generate_description`` runs synchronously inside the daemon thread the
upload handlers spawn (threading.Thread at the call sites) — so calling the
function directly exercises the real code path, including the DB write-back.

Hermetic: every configured endpoint is a local stdlib ``http.server`` mock
bound to 127.0.0.1 on a random port — no test touches the outside network.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from model.Raster_Data import RasterData
from resource.upload_data_resource import _bg_generate_description

MOCK_KEY = "upload-ai-key-456"
MOCK_MODEL = "mock-upload-model"
MOCK_REPLY = "这是一段由 mock 生成的栅格数据简介。"
RASTER_NAME = "ai_cfg_smoke_raster"
PLACEHOLDER = "暂无简介"

# Environment variables that steer the AI endpoint; cleared before every test
# so an ambient key in the developer shell can never leak into a test run.
_AI_ENV_VARS = ("AI_API_BASE", "AI_MODEL", "AI_API_KEY", "DEEPSEEK_API_KEY")

_META = {
    "bands": 3,
    "pixel_type": "uint8",
    "resolution": "0.000100 x 0.000100",
    "coordinate_system": "EPSG:4326",
    "file_size": 1024,
}


class _MockAIHandler(BaseHTTPRequestHandler):
    """Records each POST and replies with an OpenAI-shaped chat body."""

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
        payload = json.dumps({"choices": [{"message": {"role": "assistant", "content": MOCK_REPLY}}]}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
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


@pytest.fixture()
def seeded_raster(db):
    """A raster row with the placeholder introduction, removed after the test.

    Yields only the integer id: the session stays idle (no open read
    transaction) between fixture setup and the generation call, so the nested
    app context inside ``_bg_generate_description`` can commit freely.
    """
    record = RasterData(
        name=RASTER_NAME,
        alias="AI配置冒烟",
        introduction=PLACEHOLDER,
        url="",
        layer="",
        raster_file_path="",
    )
    db.session.add(record)
    db.session.flush()  # assigns id without holding an open transaction afterwards
    rid = record.id
    db.session.commit()
    try:
        yield rid
    finally:
        fresh = db.session.get(RasterData, rid)
        if fresh is not None:
            db.session.delete(fresh)
            db.session.commit()


def _run_generation(app, rid):
    _bg_generate_description(_META, RASTER_NAME, "raster", rid, RasterData, app)


def test_unconfigured_skips_silently(app, db, mock_ai_server, seeded_raster):
    """未配置任何 key → 与历史行为一致：静默跳过，无 HTTP、无落库。"""
    _run_generation(app, seeded_raster)

    assert mock_ai_server.requests == []
    assert db.session.get(RasterData, seeded_raster).introduction == PLACEHOLDER


def test_configured_endpoint_receives_upload_generation(app, db, mock_ai_server, seeded_raster, monkeypatch):
    monkeypatch.setenv("AI_API_BASE", f"http://127.0.0.1:{mock_ai_server.server_address[1]}")
    monkeypatch.setenv("AI_MODEL", MOCK_MODEL)
    monkeypatch.setenv("AI_API_KEY", MOCK_KEY)

    _run_generation(app, seeded_raster)

    assert len(mock_ai_server.requests) == 1
    req = mock_ai_server.requests[0]
    assert req["path"] == "/chat/completions"
    assert req["authorization"] == f"Bearer {MOCK_KEY}"
    assert req["content_type"] == "application/json"
    assert req["body"]["model"] == MOCK_MODEL
    assert req["body"]["messages"][0]["role"] == "user"
    assert RASTER_NAME in req["body"]["messages"][0]["content"]

    assert db.session.get(RasterData, seeded_raster).introduction == MOCK_REPLY


def test_legacy_deepseek_key_still_works(app, db, mock_ai_server, seeded_raster, monkeypatch):
    """仅设旧名 DEEPSEEK_API_KEY 的既有部署：回落生效，upload 路径照常工作。"""
    monkeypatch.setenv("AI_API_BASE", f"http://127.0.0.1:{mock_ai_server.server_address[1]}")
    monkeypatch.setenv("DEEPSEEK_API_KEY", MOCK_KEY)  # AI_API_KEY intentionally unset

    _run_generation(app, seeded_raster)

    assert len(mock_ai_server.requests) == 1
    req = mock_ai_server.requests[0]
    assert req["authorization"] == f"Bearer {MOCK_KEY}"
    # AI_MODEL 未设 → 默认模型
    assert req["body"]["model"] == "deepseek-chat"
    assert db.session.get(RasterData, seeded_raster).introduction == MOCK_REPLY
