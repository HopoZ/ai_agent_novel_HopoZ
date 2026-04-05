"""用户级设置 API（如 DeepSeek API Key）。"""

from __future__ import annotations

import os
from typing import Literal

from dotenv import load_dotenv
from fastapi import APIRouter

from agents.novel.llm_client import resolve_deepseek_api_key
from agents.persistence.env_paths import get_lores_root_resolved, get_outputs_root, get_storage_root
from agents.persistence.user_settings import (
    clear_saved_deepseek_api_key,
    get_saved_deepseek_api_key,
    save_deepseek_api_key,
)
from webapp.backend.deps import reset_agent_llm_cache
from webapp.backend.schemas import ApiKeyUpdateRequest

router = APIRouter(tags=["settings"])


def _api_key_source() -> Literal["env", "file", "none"]:
    load_dotenv()
    env_key = (os.environ.get("DEEPSEEK_API_KEY") or "").strip()
    if env_key:
        return "env"
    if get_saved_deepseek_api_key():
        return "file"
    return "none"


@router.get("/settings")
def get_settings():
    return {
        "deepseek_api_key_configured": resolve_deepseek_api_key() is not None,
        "deepseek_api_key_source": _api_key_source(),
        "storage_root": str(get_storage_root().resolve()),
        "lores_dir": str(get_lores_root_resolved().resolve()),
        "outputs_dir": str(get_outputs_root().resolve()),
    }


@router.post("/settings/api_key")
def post_api_key(body: ApiKeyUpdateRequest):
    raw = (body.api_key or "").strip()
    if raw:
        save_deepseek_api_key(raw)
    else:
        clear_saved_deepseek_api_key()
    reset_agent_llm_cache()
    return {"ok": True, "deepseek_api_key_source": _api_key_source()}
