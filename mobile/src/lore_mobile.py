"""设定加载：优先用户导入目录，其次仓库 lores，最后内置 assets。"""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def imported_lores_root() -> Path:
    env = os.getenv("FLET_APP_STORAGE_DATA")
    if env:
        return Path(env) / "imported_lores"
    return Path(__file__).resolve().parent / "_imported_lores"


def _is_ignored_markdown(file_path: Path) -> bool:
    return file_path.stem.lower() == "readme"


def _scan_markdown_files(data_path: Path) -> list[Path]:
    if not data_path.exists():
        return []
    files = [
        p
        for p in data_path.rglob("*.md")
        if p.is_file() and (not _is_ignored_markdown(p))
    ]
    files.sort(key=lambda x: x.relative_to(data_path).as_posix())
    return files


def _path_to_tag(data_path: Path, file_path: Path) -> str:
    rel = file_path.relative_to(data_path)
    return rel.with_suffix("").as_posix()


def resolve_lores_dir() -> Path:
    imp = imported_lores_root()
    if imp.is_dir() and _scan_markdown_files(imp):
        return imp
    src = Path(__file__).resolve().parent
    repo_lores = src.parent.parent / "lores"
    if repo_lores.is_dir() and _scan_markdown_files(repo_lores):
        return repo_lores
    return src / "assets" / "lores"


def lore_display_source(data_path: Path) -> str:
    try:
        if data_path.resolve() == imported_lores_root().resolve():
            return "用户导入"
    except OSError:
        pass
    src = Path(__file__).resolve().parent
    repo = (src.parent.parent / "lores").resolve()
    try:
        if data_path.resolve() == repo:
            return "仓库 lores（开发）"
    except OSError:
        pass
    return "内置 assets"


def _safe_relative_md(rel: Path) -> Path | None:
    if rel.is_absolute() or ".." in rel.parts:
        return None
    if rel.suffix.lower() != ".md":
        return None
    if rel.stem.lower() == "readme":
        return None
    return rel


def clear_imported_lores() -> None:
    root = imported_lores_root()
    if root.exists():
        shutil.rmtree(root)


def import_picked_md_files(
    items: list[tuple[str, bytes | None, str | None]],
) -> tuple[int, str]:
    """
    从系统文件选择结果写入导入目录。每项为 (显示名, 字节或 None, 本地路径或 None)。
    仅使用安全 basename 落盘，避免路径穿越。
    """
    root = imported_lores_root()
    root.mkdir(parents=True, exist_ok=True)
    n = 0
    errs: list[str] = []
    for name, data, path in items:
        raw_name = (name or "unnamed.md").replace("\\", "/")
        base = Path(raw_name).name
        if not base.lower().endswith(".md"):
            base = f"{base}.md"
        if base.lower() == "readme.md":
            continue
        blob = data
        if blob is None and path:
            try:
                blob = Path(path).read_bytes()
            except OSError as e:
                errs.append(f"{base}: {e}")
                continue
        if not blob:
            errs.append(f"{base}: 无内容")
            continue
        (root / base).write_bytes(blob)
        n += 1
    return n, "; ".join(errs)


def import_md_from_directory(src: str | Path) -> int:
    """递归复制目录下所有 .md 到导入目录，保留相对路径作为 tag。"""
    src_path = Path(src)
    if not src_path.is_dir():
        return 0
    root = imported_lores_root()
    root.mkdir(parents=True, exist_ok=True)
    n = 0
    for p in src_path.rglob("*.md"):
        if _is_ignored_markdown(p):
            continue
        rel = _safe_relative_md(p.relative_to(src_path))
        if rel is None:
            continue
        dest = root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(p.read_bytes())
        n += 1
    return n


def load_lorebook_raw(lore_tags: list[str] | None) -> tuple[str, str]:
    """
    返回 (lorebook 正文, 标签说明行)。
    无 .md 时返回空正文与提示，由调用方决定是否继续。
    """
    data_path = resolve_lores_dir()
    files = _scan_markdown_files(data_path)
    if not files:
        return "", "未找到设定：请用「导入 .md」或「导入文件夹」，或将 md 放入 assets/lores"

    if lore_tags:
        want = {str(t).strip() for t in lore_tags if str(t).strip()}
        parts: list[str] = ["### 创作百科全书 (Lorebook) ###\n"]
        for p in files:
            tag = _path_to_tag(data_path, p)
            if tag not in want:
                continue
            parts.append(f"\n【{tag}】:\n{p.read_text(encoding='utf-8')}\n")
        body = "".join(parts)
        hint = f"当前注入设定标签（lore_tags）：{', '.join(lore_tags)}"
        if len(parts) <= 1:
            return "", "按 lore_tags 未找到可用的 .md，请检查 tag"
        return body, hint

    parts = ["### 创作百科全书 (Lorebook) ###\n"]
    for p in files:
        tag = _path_to_tag(data_path, p)
        parts.append(f"\n【{tag}】:\n{p.read_text(encoding='utf-8')}\n")
    return "".join(parts), "当前注入：全部 lores md 原文"
