"""
从模型输出中抽取 JSON 对象，并在解析失败时用 LLM 再修一次。
"""

from __future__ import annotations

import json
import logging
import re
from typing import Callable, Optional

from agents._internal_marks import z7_module_mark

_MODULE_REV = z7_module_mark("lj")


def _extract_balanced_json_object(s: str, start: int) -> Optional[str]:
    """
    从 s[start] 起，按括号深度与字符串状态，截取与之匹配的最外层 {...}。
    用于嵌套很深的 JSON；不能用非贪婪正则，否则会在第一个内层 `}` 处截断。
    """
    if start < 0 or start >= len(s) or s[start] != "{":
        return None
    depth = 0
    in_string = False
    escape = False
    i = start
    while i < len(s):
        c = s[i]
        if in_string:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_string = False
            i += 1
            continue
        if c == '"':
            in_string = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
        i += 1
    return None


def _extract_from_fenced_json_block(text: str) -> Optional[str]:
    """``` 或 ```json 代码块内，从第一个 `{` 起做平衡括号截取。"""
    for m in re.finditer(r"```(?:json)?\s*\n?", text):
        inner_start = m.end()
        fence_end = text.find("```", inner_start)
        if fence_end == -1:
            continue
        inner = text[inner_start:fence_end]
        brace = inner.find("{")
        if brace == -1:
            continue
        obj = _extract_balanced_json_object(inner, brace)
        if obj:
            return obj
    return None


def extract_json_object(text: str) -> str:
    """
    从一段可能带多余内容的文本里，提取第一个 {...} 作为 JSON。
    """
    fenced = _extract_from_fenced_json_block(text)
    if fenced:
        return fenced

    start = text.find("{")
    if start != -1:
        balanced = _extract_balanced_json_object(text, start)
        if balanced:
            return balanced

    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model output.")
    return text[start : end + 1]


def json_load_with_retry(
    raw_text: str,
    fix_prompt: str,
    llm_invoke_fn: Callable[[str], str],
    *,
    logger: Optional[logging.Logger] = None,
) -> dict:
    """
    将模型输出 JSON 解析失败时，进行一次“修复 JSON”的重试。
    """
    log = logger or logging.getLogger(__name__)
    try:
        candidate = extract_json_object(raw_text)
        return json.loads(candidate)
    except Exception as e:
        log.warning("JSON parse failed, retrying. err=%s", e)
        fixed_text = llm_invoke_fn(fix_prompt)
        candidate = extract_json_object(fixed_text)
        return json.loads(candidate)
