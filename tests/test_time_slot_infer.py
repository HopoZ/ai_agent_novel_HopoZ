import sys
from pathlib import Path as _Path


def test_infer_time_slot_interval_and_legacy(tmp_path, monkeypatch):
    repo_root = _Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from agents.persistence import novel_sqlite
    from agents.persistence.storage import ensure_novel_dirs
    from agents.state.state_models import ChapterRecord, NovelState
    from webapp.backend.server import RunModeRequest, _infer_time_slot

    monkeypatch.chdir(tmp_path)

    novel_id = "11111111-1111-1111-1111-111111111111"
    ensure_novel_dirs(novel_id)

    st = NovelState.model_validate(
        {
            "meta": {"novel_id": novel_id, "initialized": True, "current_chapter_index": 0, "lore_tags": []},
            "continuity": {"time_slot": "t0", "who_is_present": [], "pov_character_id": None},
            "characters": [],
            "world": {
                "timeline": [
                    {"time_slot": "A", "summary": "a"},
                    {"time_slot": "B", "summary": "b"},
                ]
            },
            "recent_summaries": [],
        }
    )
    novel_sqlite.write_state_json(novel_id, st.model_dump_json(indent=2, ensure_ascii=False))

    ch = ChapterRecord(
        chapter_index=3,
        time_slot="C",
        pov_character_id=None,
        who_is_present=[],
        beats=[],
        content="",
        usage_metadata={},
    )
    novel_sqlite.insert_chapter_row(novel_id, ch)

    req = RunModeRequest(mode="plan_only", user_task="x", time_slot_override="MANUAL")
    assert _infer_time_slot(novel_id, req) == "MANUAL"

    req = RunModeRequest(mode="plan_only", user_task="x", insert_after_id="ev:timeline:0", insert_before_id="ev:chapter:3")
    assert _infer_time_slot(novel_id, req) == "A之后~C之前"

    req = RunModeRequest(mode="plan_only", user_task="x", insert_after_id="ev:timeline:1")
    assert _infer_time_slot(novel_id, req) == "B之后"

    req = RunModeRequest(mode="plan_only", user_task="x", insert_before_id="ev:chapter:3")
    assert _infer_time_slot(novel_id, req) == "C之前"

    req = RunModeRequest(mode="plan_only", user_task="x", insert_anchor_id="ev:timeline:0")
    assert _infer_time_slot(novel_id, req) == "A"
