"""extract_json_object：嵌套 JSON 与 markdown 代码块。"""

from agents.novel.llm_json import extract_json_object


def test_fenced_nested_json_not_truncated_at_first_brace():
    raw = """```json
{
  "meta": {"a": 1},
  "characters": [{"id": "x"}]
}
```"""
    out = extract_json_object(raw)
    import json

    data = json.loads(out)
    assert data["meta"]["a"] == 1
    assert data["characters"][0]["id"] == "x"


def test_unfenced_balanced_nested():
    raw = 'prefix\n{"outer": {"inner": 2}}\ntrailing'
    out = extract_json_object(raw)
    import json

    assert json.loads(out) == {"outer": {"inner": 2}}


def test_string_with_braces_ignored():
    raw = r'{"k": "a { not } b", "x": 1}'
    out = extract_json_object(raw)
    import json

    assert json.loads(out)["x"] == 1
