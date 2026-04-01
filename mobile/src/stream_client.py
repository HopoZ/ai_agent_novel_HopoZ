"""DeepSeek OpenAI 兼容接口：流式 chat completions。"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEFAULT_MODEL = "deepseek-chat"


def _delta_text(obj: dict[str, Any]) -> str:
    choices = obj.get("choices") or []
    if not choices:
        return ""
    delta = (choices[0] or {}).get("delta") or {}
    c = delta.get("content")
    if isinstance(c, str):
        return c
    return ""


def stream_chat_sync(
    messages: list[dict[str, str]],
    api_key: str,
    *,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.8,
    max_tokens: int = 20000,
    timeout: float = 300.0,
) -> Iterator[str]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": messages,
        "stream": True,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    with httpx.Client(timeout=timeout) as client:
        with client.stream("POST", DEEPSEEK_URL, headers=headers, json=body) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line or line.startswith(":"):
                    continue
                if not line.startswith("data: "):
                    continue
                data = line[6:].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                except json.JSONDecodeError:
                    continue
                t = _delta_text(obj)
                if t:
                    yield t


async def stream_chat_async(
    messages: list[dict[str, str]],
    api_key: str,
    *,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.8,
    max_tokens: int = 20000,
    timeout: float = 300.0,
) -> AsyncIterator[str]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": messages,
        "stream": True,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", DEEPSEEK_URL, headers=headers, json=body) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if not line or line.startswith(":"):
                    continue
                if not line.startswith("data: "):
                    continue
                data = line[6:].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                except json.JSONDecodeError:
                    continue
                t = _delta_text(obj)
                if t:
                    yield t
