"""
DeepSeek / LangChain 模型初始化与单次请求参数绑定。
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

from agents._internal_marks import z7_module_mark
from agents.persistence.user_settings import get_saved_deepseek_api_key

logger = logging.getLogger("agents.novel.llm_client")
_MODULE_REV = z7_module_mark("lc")


def resolve_deepseek_api_key() -> str | None:
    """
    解析顺序：环境变量 DEEPSEEK_API_KEY（含 .env）> 本地 user_settings 文件。
    """
    load_dotenv()
    env_key = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
    if env_key:
        return env_key
    saved = get_saved_deepseek_api_key()
    if saved:
        return saved
    return None


def init_deepseek_chat():
    """
    构造默认 DeepSeek Chat 模型（DEEPSEEK_API_KEY：环境变量或 Web「API 密钥」保存）。
    Web 服务可在未调用前不触发，以便无 key 时仍能启动。
    """
    api_key = resolve_deepseek_api_key()
    if not api_key:
        raise ValueError(
            "未配置 DeepSeek API Key：请在项目根目录 .env 中设置 DEEPSEEK_API_KEY，"
            "或在网页右上角「API 密钥」中填写并保存。"
        )

    return init_chat_model(
        "deepseek-chat",
        model_provider="openai",
        api_key=api_key,
        base_url="https://api.deepseek.com/v1",
        temperature=0.7,
        output_version="v1",
        max_tokens=20000,
    )


def bind_llm_options(base: Any, llm_options: Optional[Dict[str, Any]] = None) -> Any:
    """
    按单次请求覆盖 sampling 参数（temperature / top_p / max_tokens）。
    未传或全为空时返回 base。
    """
    if not llm_options:
        return base
    kwargs: Dict[str, Any] = {}
    for key in ("temperature", "top_p", "max_tokens"):
        v = llm_options.get(key)
        if v is not None:
            kwargs[key] = v
    if not kwargs:
        return base
    bind = getattr(base, "bind", None)
    if callable(bind):
        try:
            return bind(**kwargs)
        except Exception as e:
            logger.warning("model.bind(%s) failed, using base model: %s", kwargs, e)
    return base
