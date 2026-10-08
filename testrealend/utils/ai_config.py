"""共享 AI 接口配置：所有 AI 调用（chat 端点、上传自动描述）统一经由此处解析。

调用方在使用时实时读取环境变量，默认指向 DeepSeek 官方 API；
设置 AI_API_BASE 可指向任意 OpenAI 兼容端点（如本地 Ollama）。
"""

import os

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
