"""可写数据目录：支持环境变量，供 Electron 安装版将数据放到 userData。"""

from __future__ import annotations

import os
from pathlib import Path


def get_storage_root() -> Path:
    p = os.environ.get("NOVEL_AGENT_STORAGE_DIR", "").strip()
    if p:
        return Path(p)
    return Path("storage")


def get_outputs_root() -> Path:
    p = os.environ.get("NOVEL_AGENT_OUTPUTS_DIR", "").strip()
    if p:
        return Path(p)
    # 与 NOVEL_AGENT_STORAGE_DIR 为同一应用数据根时，输出落在其下 outputs/（Electron 安装版）
    if os.environ.get("NOVEL_AGENT_STORAGE_DIR", "").strip():
        return get_storage_root() / "outputs"
    return Path("outputs")


def try_get_lores_dir_from_env() -> Path | None:
    """
    可选覆盖。若设置了 NOVEL_AGENT_LORES_DIR 则用之；
    否则返回 None，由 LoreLoader 在已设置 NOVEL_AGENT_STORAGE_DIR 时用 STORAGE_DIR/lores，否则用仓库根 lores。
    """
    p = os.environ.get("NOVEL_AGENT_LORES_DIR", "").strip()
    return Path(p) if p else None


def get_lores_root_resolved() -> Path:
    """当前生效的 lores 根目录（与 LoreLoader 逻辑一致，供 API 展示路径）。"""
    o = try_get_lores_dir_from_env()
    if o is not None:
        return o
    if os.environ.get("NOVEL_AGENT_STORAGE_DIR", "").strip():
        return get_storage_root() / "lores"
    return Path(__file__).resolve().parents[2] / "lores"
