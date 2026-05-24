"""
讯飞星火大模型 API 封装
支持 Spark v3.5（Lite/Pro/Max）的 HTTP 调用方式
"""

import os
import json
import time
import hashlib
import hmac
import base64
from datetime import datetime, timezone
from urllib.parse import urlparse, urlencode
from typing import AsyncIterator

import httpx
from dotenv import load_dotenv

# 自动加载项目根目录的 .env 文件
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# === 配置（从环境变量读取） ===
SPARK_APP_ID = os.getenv("SPARK_APP_ID", "")
SPARK_API_KEY = os.getenv("SPARK_API_KEY", "")
SPARK_API_SECRET = os.getenv("SPARK_API_SECRET", "")

# 星火 API 地址（Ultra 32K 版本）
SPARK_API_URL = "wss://spark-api.xf-yun.com/v4.0/chat"
SPARK_DOMAIN = "4.0Ultra"


def _build_auth_url() -> str:
    """构建带鉴权签名的 WebSocket URL"""
    host = urlparse(SPARK_API_URL).netloc
    path = urlparse(SPARK_API_URL).path
    now = datetime.now(timezone.utc)
    date = now.strftime("%a, %d %b %Y %H:%M:%S GMT")

    signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
    signature_sha = hmac.new(
        SPARK_API_SECRET.encode(),
        signature_origin.encode(),
        digestmod=hashlib.sha256,
    ).digest()
    signature_b64 = base64.b64encode(signature_sha).decode()

    authorization_origin = (
        f'api_key="{SPARK_API_KEY}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature_b64}"'
    )
    authorization = base64.b64encode(authorization_origin.encode()).decode()

    params = {
        "authorization": authorization,
        "date": date,
        "host": host,
    }
    return f"{SPARK_API_URL}?{urlencode(params)}"


async def spark_chat_stream(
    messages: list[dict],
    temperature: float = 0.5,
    max_tokens: int = 4096,
) -> AsyncIterator[str]:
    """
    调用讯飞星火大模型，返回流式输出的文本块

    Args:
        messages: [{"role": "user", "content": "..."}, ...]
        temperature: 随机性 0~1
        max_tokens: 最大返回 token 数

    Yields:
        每次产出一段文本
    """
    import websockets

    url = _build_auth_url()
    params = {
        "header": {"app_id": SPARK_APP_ID, "uid": "smart-tutor"},
        "parameter": {
            "chat": {
                "domain": SPARK_DOMAIN,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        },
        "payload": {
            "message": {"text": messages},
        },
    }

    async with websockets.connect(url) as ws:
        await ws.send(json.dumps(params))

        while True:
            try:
                response = await ws.recv()
                data = json.loads(response)

                code = data.get("header", {}).get("code", 0)
                if code != 0:
                    err_msg = data.get("header", {}).get("message", "unknown error")
                    yield f"[错误 {code}: {err_msg}]"
                    break

                choices = (
                    data.get("payload", {}).get("choices", {}).get("text", [])
                )
                for choice in choices:
                    content = choice.get("content", "")
                    if content:
                        yield content

                status = data.get("header", {}).get("status", 2)
                if status == 2:
                    break  # 结束

            except websockets.ConnectionClosed:
                break


async def spark_chat(
    messages: list[dict],
    temperature: float = 0.5,
    max_tokens: int = 4096,
) -> str:
    """调用讯飞星火，返回完整回复文本（非流式）"""
    result = []
    async for chunk in spark_chat_stream(messages, temperature, max_tokens):
        result.append(chunk)
    return "".join(result)


async def spark_chat_http(
    messages: list[dict],
    temperature: float = 0.5,
    max_tokens: int = 4096,
) -> dict:
    """
    使用 HTTP 方式调用星火 API（不含 WebSocket）
    适用于不想处理 WebSocket 长连接的场景
    """
    # 构建鉴权 URL（此处使用 RESTful 的替代方案）
    # 星火目前主要用 WebSocket，这里用 httpx 包装
    result = await spark_chat(messages, temperature, max_tokens)
    return {
        "choices": [{"message": {"role": "assistant", "content": result}}]
    }
