"""用户级设置（如 DeepSeek API Key），持久化在 storage 目录下，供桌面安装版使用。"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

from agents.persistence.env_paths import get_storage_root

_SETTINGS_NAME = "user_settings.json"


def _settings_path() -> Path:
    return get_storage_root() / _SETTINGS_NAME


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    _ensure_parent(path)
    fd, tmp = tempfile.mkstemp(prefix=".user_settings_", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def load_settings_file() -> dict[str, Any]:
    path = _settings_path()
    if not path.is_file():
        return {}
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def get_saved_deepseek_api_key() -> Optional[str]:
    v = load_settings_file().get("deepseek_api_key")
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def save_deepseek_api_key(api_key: str) -> None:
    data = load_settings_file()
    key = (api_key or "").strip()
    if key:
        data["deepseek_api_key"] = key
    else:
        data.pop("deepseek_api_key", None)
    path = _settings_path()
    if not data:
        if path.is_file():
            path.unlink()
        return
    _atomic_write_json(path, data)


def clear_saved_deepseek_api_key() -> None:
    save_deepseek_api_key("")
