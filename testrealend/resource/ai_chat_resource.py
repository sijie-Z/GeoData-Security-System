"""AI Chat endpoint — calls an OpenAI-compatible chat API with system knowledge context."""

import json
import logging
import os

from flask import Response, request, stream_with_context
from flask_jwt_extended import get_jwt_identity, jwt_required, verify_jwt_in_request
from flask_restful import Resource

logger = logging.getLogger(__name__)

# ── AI 接口配置 ──
# 默认指向 DeepSeek 官方 API，未配置时行为与历史版本一致；
# 设置 AI_API_BASE 可指向任意 OpenAI 兼容端点（如本地 Ollama）。
DEFAULT_AI_API_BASE = "https://api.deepseek.com"
DEFAULT_AI_MODEL = "deepseek-chat"


def _get_ai_config():
    """从环境变量解析 (api_base, api_key, model)，按请求实时读取。

    ``AI_API_KEY`` 优先，回落旧名 ``DEEPSEEK_API_KEY`` 以兼容既有部署。
    """
    api_base = os.environ.get("AI_API_BASE") or DEFAULT_AI_API_BASE
    api_key = os.environ.get("AI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY") or ""
    model = os.environ.get("AI_MODEL") or DEFAULT_AI_MODEL
    return api_base, api_key, model


def _chat_completions_url(api_base):
    """将 OpenAI 兼容的 base URL 拼装为 chat completions 端点。"""
    return api_base.rstrip("/") + "/chat/completions"


# ── 系统知识库（注入 System Prompt） ──
SYSTEM_PROMPT = """你是"地安智助"——地理空间数据安全追踪系统的 AI 智能助手。你的职责是帮助用户理解和使用本系统。

## 系统概述
本系统是一个面向地理空间数据（矢量数据和遥感栅格数据）的全生命周期安全管理平台，核心功能包括：
数据目录浏览与检索、数据申请与双级审批、数字水印嵌入与提取、数据溯源与版权证明、数据下载与回收审议。

## 用户角色
- 员工（Employee）：可以浏览数据目录、提交数据申请、下载已审批数据、查看操作历史。
- 管理员（Admin）：分为 admin1（一审+矢量水印）、admin2（二审+栅格水印）、admin3（附加审议+提取验证），
  还有超级管理员拥有全部权限。

## 数据申请流程
1. 员工在"数据目录"页面找到需要的数据，点击"申请"。
2. 申请提交后进入"待一审"状态，由管理员1审核。
3. 一审通过后进入"待二审"状态，由管理员2审核。
4. 二审通过后，系统自动为数据嵌入数字水印，员工即可在"数据下载"页面下载。
5. 如果申请被拒绝，员工可以查看拒绝理由后重新申请。

## 数字水印技术
系统支持两种数据类型的水印保护：

### 矢量数据水印
- 通过修改坐标值的低位二进制位嵌入水印信息。
- 坐标四舍五入到小数点后固定位数时会产生量子化误差，可能破坏部分水印比特。
- 适合数据溯源和版权证明，即使有比特错误，QR码仍可通过错误校正识别。

### 栅格（遥感）数据水印
- 支持三种算法：LSB（最低有效位）、DWT（离散小波变换）、直方图平移。
- LSB：隐写质量优秀（PSNR高），但水印脆弱，任何攻击都会破坏。适合篡改检测。
- DWT+QIM：频域嵌入，理论上更鲁棒。
- 直方图平移：对自然图像数学上不可行（需要纯色图像）。

## 数据溯源
每份下载的数据都嵌入了唯一水印。如果数据被非法传播：
1. 从泄露数据中提取水印。
2. 解码水印信息（包含下载者编号、时间戳等）。
3. 实现数据泄露的责任追溯。

## 常见问题
- 忘记密码：请联系管理员重置。
- 申请被拒绝：查看拒绝理由，修改后重新提交。
- 下载的数据打不开：矢量数据用 QGIS/ArcGIS 打开，栅格数据用 GDAL/遥感软件打开。
- 水印验证失败：量子化误差是正常现象，QR码的纠错功能可以容忍一定程度的比特错误。
- 如何成为管理员：在"申请管理员"页面提交申请，需要现有管理员投票通过。

## 回收审议
管理员可以发起"数据回收提议"，其他管理员投票决定是否回收某份已分发的数据。
回收后该数据将不再可供下载。

## 回答原则
- 用中文回答，语言简洁友好。
- 如果用户问的问题超出系统范围，礼貌说明你只能回答与本系统相关的问题。
- 如果不确定答案，建议用户联系管理员或查看系统帮助页面。
"""


class AIChatResource(Resource):
    """AI 智能问答接口
    ---
    tags: [AI]
    security: [Bearer: []]
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required: [message]
          properties:
            message: {type: string, description: 用户消息}
            history:
              type: array
              description: 对话历史
              items:
                type: object
                properties:
                  role: {type: string, enum: [user, assistant]}
                  content: {type: string}
    responses:
      200: {description: AI 回复}
      500: {description: 服务不可用}
    """

    @jwt_required()
    def post(self):
        data = request.get_json() or {}
        user_message = (data.get("message") or "").strip()
        history = data.get("history") or []

        if not user_message:
            return {"status": False, "msg": "消息不能为空"}, 400

        # 构建消息列表
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        # 加入对话历史（最多保留最近 10 轮）
        for item in history[-20:]:
            role = item.get("role", "user")
            content = item.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_message})

        # 调用 AI 服务（OpenAI 兼容端点）
        api_base, api_key, model = _get_ai_config()
        if not api_key:
            return {
                "status": False,
                "msg": "AI 服务未配置（缺少 AI_API_KEY 环境变量）",
            }, 503

        try:
            import httpx

            # 直接 HTTP 调用（不依赖 openai 库，避免兼容性问题）
            resp = httpx.post(
                _chat_completions_url(api_base),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": 1024,
                    "temperature": 0.7,
                },
                timeout=25.0,
            )
            resp.raise_for_status()
            data = resp.json()
            reply = data["choices"][0]["message"]["content"]
            return {"status": True, "data": {"reply": reply}}, 200

        except ImportError:
            return {"status": False, "msg": "服务端缺少 httpx 库，请 pip install httpx"}, 500
        except Exception as e:
            logger.error(f"AI API 调用失败: {e}", exc_info=True)
            return {"status": False, "msg": f"AI 服务暂时不可用: {str(e)[:200]}"}, 502


def _build_messages(user_message, history):
    """Build the messages list for the chat API."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for item in history[-20:]:
        role = item.get("role", "user")
        content = item.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})
    return messages


class AIChatStreamResource(Resource):
    """SSE streaming AI chat endpoint.

    Returns ``text/event-stream`` with incremental ``data:`` frames.
    Each frame is a JSON object: ``{"token": "..."}`` or ``{"done": true}``.
    """

    @jwt_required()
    def post(self):
        data = request.get_json() or {}
        user_message = (data.get("message") or "").strip()
        history = data.get("history") or []

        if not user_message:
            return {"status": False, "msg": "消息不能为空"}, 400

        api_base, api_key, model = _get_ai_config()
        if not api_key:
            return {
                "status": False,
                "msg": "AI 服务未配置（缺少 AI_API_KEY 环境变量）",
            }, 503

        messages = _build_messages(user_message, history)

        def generate():
            try:
                import httpx

                with (
                    httpx.Client(timeout=60.0) as client,
                    client.stream(
                        "POST",
                        _chat_completions_url(api_base),
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model,
                            "messages": messages,
                            "max_tokens": 1024,
                            "temperature": 0.7,
                            "stream": True,
                        },
                    ) as resp,
                ):
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        payload = line[6:]
                        if payload.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(payload)
                            delta = chunk["choices"][0].get("delta", {})
                            token = delta.get("content", "")
                            if token:
                                yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
                yield f"data: {json.dumps({'done': True})}\n\n"
            except ImportError:
                yield f"data: {json.dumps({'error': '服务端缺少 httpx 库'})}\n\n"
            except Exception as e:
                logger.error(f"AI SSE 调用失败: {e}", exc_info=True)
                yield f"data: {json.dumps({'error': f'AI 服务暂时不可用: {str(e)[:200]}'})}\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
