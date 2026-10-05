"""AI Chat Interface Multi-Scenario Test Script

Tests the /api/ai/chat endpoint against a running backend at http://127.0.0.1:5003.
Uses httpx; prints status codes and key response fields.
Chinese strings are handled via repr() to avoid encoding issues in Windows console.
A detailed UTF-8 report is written to test_ai_chat_report.txt.
"""

import os
import sys
import httpx

BASE = "http://127.0.0.1:5003"
TIMEOUT = 30.0


def safe(text: str, max_len: int = 120) -> str:
    """Truncate and repr-ify a string for safe console output."""
    r = repr(text)
    return r[:max_len] + "..." if len(r) > max_len else r


# ── Test Results Collector ──
results: list[dict] = []


def record(name: str, expected: int, actual: int, body: dict, detail_lines: list[str] | None = None):
    ok = expected == actual
    entry = {
        "name": name,
        "expected": expected,
        "actual": actual,
        "ok": ok,
        "body": body,
        "detail": detail_lines or [],
    }
    results.append(entry)
    tag = "PASS" if ok else "FAIL"
    print(f"\n{'='*60}")
    print(f"[{tag}] {name}")
    print(f"  Expected status: {expected}  |  Actual: {actual}")
    for key in ("status", "msg", "data"):
        if key in body:
            val = body[key]
            if isinstance(val, dict):
                for k2, v2 in val.items():
                    entry["detail"].append(f"{key}.{k2}: {str(v2)[:200]}")
                    print(f"  {key}.{k2}: {safe(str(v2))}")
            else:
                entry["detail"].append(f"{key}: {str(val)[:200]}")
                print(f"  {key}: {safe(str(val))}")
    print(f"{'='*60}")


def main():
    client = httpx.Client(base_url=BASE, timeout=TIMEOUT)

    # ────────────────────────────────────────────────
    # 1. Login to get JWT token
    # ────────────────────────────────────────────────
    print("\n>>> Scenario 1: Login (admin / admin123)")
    resp = client.post("/api/login", json={
        "username": "admin",
        "password": "admin123",
        "role": "admin",
    })
    body = resp.json()
    record("Login", 200, resp.status_code, body)

    token = body.get("access_token") or body.get("data", {}).get("access_token", "")
    if not token:
        print("FATAL: No access_token in login response. Cannot continue.")
        print(f"Full response: {safe(str(body), 500)}")
        client.close()
        sys.exit(1)

    headers = {"Authorization": f"Bearer {token}"}
    print(f"  Token obtained (first 40 chars): {token[:40]}...")

    # ────────────────────────────────────────────────
    # 2. Normal Chinese message
    # ────────────────────────────────────────────────
    print("\n>>> Scenario 2: Normal Chinese message")
    resp = client.post("/api/ai/chat", json={
        "message": "你好，请介绍一下数字水印技术。",
    }, headers=headers)
    body = resp.json()
    record("Normal Chinese Message", 200, resp.status_code, body)

    # ────────────────────────────────────────────────
    # 3. Multi-turn conversation with history
    # ────────────────────────────────────────────────
    print("\n>>> Scenario 3: Multi-turn conversation with history")
    history = [
        {"role": "user", "content": "什么是矢量数据？"},
        {"role": "assistant", "content": "矢量数据是用点、线、面来表示地理要素的数据格式，常见格式有 Shapefile、GeoJSON 等。"},
        {"role": "user", "content": "矢量数据水印是怎么嵌入的？"},
        {"role": "assistant", "content": "通过修改坐标值的低位二进制位来嵌入水印信息。"},
    ]
    resp = client.post("/api/ai/chat", json={
        "message": "那提取水印时会有什么问题？",
        "history": history,
    }, headers=headers)
    body = resp.json()
    record("Multi-turn with History", 200, resp.status_code, body)

    # ────────────────────────────────────────────────
    # 4. Empty message (should return 400)
    # ────────────────────────────────────────────────
    print("\n>>> Scenario 4: Empty message (expect 400)")
    resp = client.post("/api/ai/chat", json={
        "message": "",
    }, headers=headers)
    body = resp.json()
    record("Empty Message", 400, resp.status_code, body)

    # Also test whitespace-only
    print("\n>>> Scenario 4b: Whitespace-only message (expect 400)")
    resp = client.post("/api/ai/chat", json={
        "message": "   ",
    }, headers=headers)
    body = resp.json()
    record("Whitespace-Only Message", 400, resp.status_code, body)

    # ────────────────────────────────────────────────
    # 5. No token (should return 401)
    # ────────────────────────────────────────────────
    print("\n>>> Scenario 5: No token (expect 401)")
    resp = client.post("/api/ai/chat", json={
        "message": "Hello without token",
    })
    body = resp.json()
    record("No Token", 401, resp.status_code, body)

    # ────────────────────────────────────────────────
    # 6. Very long message (~2000 chars)
    # ────────────────────────────────────────────────
    print("\n>>> Scenario 6: Long message (~2000 chars)")
    long_msg = "请详细介绍系统的全部功能模块，" * 100  # ~1900 chars
    print(f"  Message length: {len(long_msg)} chars")
    resp = client.post("/api/ai/chat", json={
        "message": long_msg,
    }, headers=headers)
    body = resp.json()
    record("Long Message (~2000 chars)", 200, resp.status_code, body)

    client.close()

    # ────────────────────────────────────────────────
    # Summary
    # ────────────────────────────────────────────────
    passed = sum(1 for r in results if r["ok"])
    total = len(results)

    print("\n" + "=" * 60)
    print("  TEST SUMMARY")
    print("=" * 60)
    for r in results:
        tag = "PASS" if r["ok"] else "FAIL"
        print(f"  [{tag}] {r['name']}  (expected {r['expected']}, got {r['actual']})")
    print(f"\n  Total: {passed}/{total} passed")
    print("=" * 60)

    # Write readable report to UTF-8 file (Windows console mangles CJK)
    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_ai_chat_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("AI Chat Interface Test Report\n")
        f.write(f"Server: {BASE}\n")
        f.write("=" * 60 + "\n\n")
        for i, entry in enumerate(results, 1):
            f.write(f"[{i}] {entry['name']}\n")
            f.write(f"    Status: {entry['actual']} (expected {entry['expected']}) -> {'PASS' if entry['ok'] else 'FAIL'}\n")
            for line in entry["detail"]:
                f.write(f"    {line}\n")
            f.write("\n")
        f.write("=" * 60 + "\n")
        f.write(f"Total: {passed}/{total} passed\n")

    print(f"\nDetailed report written to: {report_path}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
