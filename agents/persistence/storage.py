from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from agents.persistence import novel_sqlite
from agents.persistence.env_paths import get_storage_root
from agents.state.state_models import ChapterRecord, ContinuityState, NovelMeta, NovelState, WorldState


def _novel_dir(novel_id: str) -> Path:
    UUID(novel_id)
    return get_storage_root() / "novels" / novel_id


def get_chapters_dir(novel_id: str) -> Path:
    return _novel_dir(novel_id) / "chapters"


def ensure_novel_dirs(novel_id: str) -> None:
    d = _novel_dir(novel_id)
    d.mkdir(parents=True, exist_ok=True)
    get_chapters_dir(novel_id).mkdir(parents=True, exist_ok=True)


def load_state(novel_id: str) -> Optional[NovelState]:
    state: Optional[NovelState] = None
    if novel_sqlite.db_exists(novel_id):
        raw = novel_sqlite.read_state_json(novel_id)
        if raw:
            try:
                import json

                state = NovelState.model_validate(json.loads(raw))
            except Exception:
                state = None

    chapters = list_chapters(novel_id)
    if not chapters:
        if state is not None:
            from agents.persistence.graph_tables import ensure_timeline_stable_ids

            ensure_timeline_stable_ids(novel_id, state)
            try:
                save_state(novel_id, state)
            except Exception:
                pass
        return state

    latest = max(chapters, key=lambda c: (c.chapter_index, c.created_at))
    if state is None:
        state = NovelState(
            meta=NovelMeta(
                novel_id=novel_id,
                novel_title="未命名小说",
                initialized=False,
                current_chapter_index=int(latest.chapter_index),
            ),
            continuity=ContinuityState(
                time_slot=str(latest.time_slot or "未设置"),
                pov_character_id=latest.pov_character_id,
                who_is_present=(latest.who_is_present or []),
            ),
            characters=[],
            world=WorldState(),
            recent_summaries=[],
        )
    else:
        state.meta.current_chapter_index = int(latest.chapter_index)
        state.continuity.time_slot = str(latest.time_slot or state.continuity.time_slot or "未设置")
        state.continuity.pov_character_id = latest.pov_character_id or state.continuity.pov_character_id
        state.continuity.who_is_present = latest.who_is_present or []

    if state is not None:
        from agents.persistence.graph_tables import ensure_timeline_stable_ids

        ensure_timeline_stable_ids(novel_id, state)

    try:
        save_state(novel_id, state)
    except Exception:
        pass
    return state


def save_state(novel_id: str, state: NovelState) -> None:
    ensure_novel_dirs(novel_id)
    state_to_save = state.model_copy(deep=True)
    for c in state_to_save.characters or []:
        c.relationships = {}
    novel_sqlite.write_state_json(novel_id, state_to_save.model_dump_json(indent=2, ensure_ascii=False))


def load_chapter(novel_id: str, chapter_index: int) -> Optional[ChapterRecord]:
    if not novel_sqlite.db_exists(novel_id):
        return None
    hits: List[ChapterRecord] = []
    for rec in novel_sqlite.load_all_chapter_records(novel_id):
        if rec.chapter_index == chapter_index:
            hits.append(rec)
    if not hits:
        return None
    return max(hits, key=lambda c: c.created_at)


def list_chapters(novel_id: str) -> List[ChapterRecord]:
    if not novel_sqlite.db_exists(novel_id):
        return []
    return novel_sqlite.load_all_chapter_records(novel_id)


def list_chapters_latest_per_index(novel_id: str) -> List[ChapterRecord]:
    by_idx: dict[int, ChapterRecord] = {}
    for c in list_chapters(novel_id):
        prev = by_idx.get(c.chapter_index)
        if prev is None or c.created_at > prev.created_at:
            by_idx[c.chapter_index] = c
    return sorted(by_idx.values(), key=lambda c: c.chapter_index)


def save_chapter(novel_id: str, chapter: ChapterRecord, chapter_preset_name: Optional[str] = None) -> Path:
    ensure_novel_dirs(novel_id)
    preset = (chapter_preset_name or chapter.chapter_preset_name or "").strip()
    if preset:
        chapter.chapter_preset_name = preset
    novel_sqlite.insert_chapter_row(novel_id, chapter)
    return novel_sqlite.get_db_path(novel_id)
