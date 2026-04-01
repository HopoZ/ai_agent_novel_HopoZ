"""状态压缩注入。包结构与职责见 `agents/README.md`。"""

from __future__ import annotations

import json
from typing import Dict, Optional, Set

from agents._internal_marks import z7_module_mark
from agents.persistence.graph_tables import timeline_index_for_node_id, timeline_next_graph_neighbors

from .state_models import NovelState

_MODULE_REV = z7_module_mark("sc")


def select_related_character_ids(
    state: NovelState,
    user_task: str,
    pov_character_ids_override: Optional[list[str]] = None,
    supporting_character_ids: Optional[list[str]] = None,
    include_continuity_present: bool = True,
) -> Set[str]:
    ids = {c.character_id for c in (state.characters or []) if c.character_id}
    selected: Set[str] = set()
    for x in (pov_character_ids_override or []):
        if x in ids:
            selected.add(x)
    for x in (supporting_character_ids or []):
        if x in ids:
            selected.add(x)
    if include_continuity_present:
        for p in (state.continuity.who_is_present or []):
            if p.character_id in ids:
                selected.add(p.character_id)
    task = user_task or ""
    for cid in ids:
        if cid and (cid in task):
            selected.add(cid)
    if not selected and state.continuity.pov_character_id:
        selected.add(state.continuity.pov_character_id)
    return selected


def compact_state_for_prompt(
    state: NovelState,
    user_task: str,
    time_slot_hint: Optional[str] = None,
    pov_character_ids_override: Optional[list[str]] = None,
    supporting_character_ids: Optional[list[str]] = None,
    minimal_context: bool = False,
    strict_no_supporting: bool = False,
    timeline_n: int = 6,
    max_chars: int = 9000,
    novel_id: Optional[str] = None,
    focus_timeline_event_id: Optional[str] = None,
    omit_world_timeline: bool = False,
) -> str:
    rel_ids = select_related_character_ids(
        state=state,
        user_task=user_task,
        pov_character_ids_override=pov_character_ids_override,
        supporting_character_ids=supporting_character_ids,
        include_continuity_present=(not minimal_context),
    )
    compact_chars = []
    for c in state.characters or []:
        if rel_ids and c.character_id not in rel_ids:
            continue
        rel = [] if strict_no_supporting else list((c.relationships or {}).items())[:3]
        compact_chars.append(
            {
                "character_id": c.character_id,
                "relationships": dict(rel),
                "goals": (c.goals or [])[:2],
                "known_facts": (c.known_facts or [])[:3],
            }
        )

    task = user_task or ""
    key_rules = state.world.key_rules or {}
    picked_rules: Dict[str, str] = {}
    for k, v in key_rules.items():
        if (k and k in task) or any((cid and cid in (k + v)) for cid in rel_ids):
            picked_rules[k] = v
    if not picked_rules:
        for i, (k, v) in enumerate(key_rules.items()):
            if i >= 3:
                break
            picked_rules[k] = v

    timeline = list(state.world.timeline or [])
    picked_tl: list = []
    if omit_world_timeline:
        picked_tl = []
    elif not minimal_context:
        used_focus_slice = False
        if novel_id and focus_timeline_event_id:
            fid = str(focus_timeline_event_id).strip()
            fi = timeline_index_for_node_id(state, fid)
            if fi is not None and 0 <= fi < len(timeline):
                used_focus_slice = True
                preds, succs = timeline_next_graph_neighbors(novel_id, fid)
                idx_set: Set[int] = {fi}
                for pid in preds:
                    j = timeline_index_for_node_id(state, pid)
                    if j is not None and 0 <= j < len(timeline):
                        idx_set.add(j)
                for sid in succs:
                    j = timeline_index_for_node_id(state, sid)
                    if j is not None and 0 <= j < len(timeline):
                        idx_set.add(j)
                if len(idx_set) == 1:
                    for k in range(max(0, len(timeline) - max(1, timeline_n)), len(timeline)):
                        idx_set.add(k)
                picked_tl = [timeline[i] for i in sorted(idx_set)]
        if not used_focus_slice:
            picked_tl = timeline[-max(1, timeline_n) :]
    # 仅当章节已「归属已有时间线事件」时，才按 time_slot 从全表补条目。
    # 新建事件且未选上下沿时无 focus_timeline_event_id：若仍用 `hint in time_slot` 子串匹配，
    # 会把凡含该片段的事件几乎全部拼进 prompt（token 暴涨、叙事干扰）。
    if (
        (not omit_world_timeline)
        and (not minimal_context)
        and time_slot_hint
        and focus_timeline_event_id
    ):
        fid = str(focus_timeline_event_id).strip()
        if timeline_index_for_node_id(state, fid) is not None:
            hint = (time_slot_hint or "").strip()
            if hint:

                def _row_key(ev) -> tuple:
                    eid = getattr(ev, "event_id", None) or ""
                    if eid:
                        return ("id", eid)
                    return ("legacy", (ev.time_slot or "").strip(), (ev.summary or "").strip())

                seen = {_row_key(x) for x in picked_tl}
                for t in timeline:
                    if (t.time_slot or "").strip() != hint:
                        continue
                    k = _row_key(t)
                    if k in seen:
                        continue
                    picked_tl.append(t)
                    seen.add(k)

    payload = {
        "meta": {
            "novel_id": state.meta.novel_id,
            "novel_title": state.meta.novel_title,
            "initialized": state.meta.initialized,
            "current_chapter_index": state.meta.current_chapter_index,
        },
        "continuity": {
            "time_slot": (time_slot_hint or state.continuity.time_slot),
            "pov_character_id": state.continuity.pov_character_id,
            "who_is_present": [] if minimal_context else [p.model_dump() for p in (state.continuity.who_is_present or [])],
        },
        "characters": compact_chars,
        "world": {
            "key_rules": picked_rules,
            "timeline": [t.model_dump(mode="json") for t in picked_tl],
        },
    }
    s = json.dumps(payload, ensure_ascii=False, indent=2)
    if len(s) > max_chars:
        return s[:max_chars] + "\n...[truncated]"
    return s


def format_state_for_prompt(state: NovelState, max_chars: int = 12000) -> str:
    payload = {
        "meta": state.meta.model_dump(mode="json"),
        "continuity": state.continuity.model_dump(),
        "characters": [
            {
                "character_id": c.character_id,
                "relationships": c.relationships,
                "goals": c.goals,
                "known_facts": c.known_facts,
                "description": c.description,
            }
            for c in state.characters
        ],
        "world": {
            "key_rules": state.world.key_rules,
            "factions": state.world.factions,
            "timeline": [t.model_dump(mode="json") for t in state.world.timeline[-10:]],
            "open_questions": state.world.open_questions[-30:],
        },
        "recent_summaries": state.recent_summaries[-10:],
    }
    s = json.dumps(payload, ensure_ascii=False, indent=2)
    if len(s) > max_chars:
        return s[:max_chars] + "\n...[truncated]"
    return s
