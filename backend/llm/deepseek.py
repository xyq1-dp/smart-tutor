"""
DeepSeek API 封装（OpenAI 兼容格式）
供 Profile / Path / Evaluation / Tutor / AntiHallucination Agent 使用
"""

import os
import json
from typing import AsyncIterator

import httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


async def deepseek_chat(
    messages: list[dict],
    temperature: float = 0.5,
    max_tokens: int = 4096,
) -> str:
    """调用 DeepSeek，返回完整回复文本"""
    result = []
    async for chunk in deepseek_chat_stream(messages, temperature, max_tokens):
        result.append(chunk)
    return "".join(result)


async def deepseek_chat_stream(
    messages: list[dict],
    temperature: float = 0.5,
    max_tokens: int = 4096,
) -> AsyncIterator[str]:
    """调用 DeepSeek，流式输出文本块"""
    url = f"{DEEPSEEK_BASE_URL}/v1/chat/completions"

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", url, json=payload, headers=headers) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                yield f"[错误 {resp.status_code}: {body.decode()[:200]}]"
                return

            async for line in resp.aiter_lines():
                if line and line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = (
                            data.get("choices", [{}])[0]
                            .get("delta", {})
                            .get("content", "")
                        )
                        if delta:
                            yield delta
                    except (json.JSONDecodeError, KeyError):
                        pass
