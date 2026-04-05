# cli 版：多轮对话 + 每轮流式输出；退出时落盘全文。设定仅读 lores md 原文（不读摘要缓存）。

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from typing import List, Optional, Tuple

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.messages import BaseMessage, convert_to_openai_messages
from openai import OpenAI

from agents.lore.loader import LoreLoader
from agents.text_utils import openai_chat_delta_reasoning_and_answer, parse_ai_chunk_text

try:
    import winsound
except ImportError:
    winsound = None  # type: ignore[misc, assignment]


def _load_cli_lorebook_raw(loader: LoreLoader, lore_tags: Optional[list[str]]) -> str:
    """CLI 专用：只从 lores/*.md 拼正文，不访问摘要缓存。"""
    if lore_tags:
        book = loader.get_lore_by_tags(list(lore_tags))
        body = book.replace("### 创作百科全书 (Lorebook) ###", "").strip()
        if not body:
            raise ValueError("按 lore_tags 未找到可用的 .md 内容，请检查 tag 是否在 lores 中存在。")
        return book
    text = loader.get_all_lore()
    if not text.strip():
        raise ValueError("lores 目录下没有找到 .md 设定文件，无法生成 lorebook。")
    return text


DEFAULT_REASONER_MODEL = "deepseek-reasoner"
DEFAULT_CHAT_MODEL = "deepseek-chat"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
_REASONER_MAX_TOKENS = 32768
_CHAT_MAX_TOKENS = 20000


class WritingAgent:
    def __init__(self, model_name: str = DEFAULT_REASONER_MODEL):
        load_dotenv()
        self.lore_loader = LoreLoader()
        self.model_name = model_name
        self._reasoner_mode = "reasoner" in model_name.lower()
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if self._reasoner_mode:
            self.model = None
            self._oai = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)
        else:
            self._oai = None
            self.model = init_chat_model(
                model_name,
                model_provider="openai",
                api_key=api_key,
                base_url=DEEPSEEK_BASE_URL,
                temperature=0.8,
                output_version="v1",
                max_tokens=_CHAT_MAX_TOKENS,
            )

    def open_session(self, lore_tags: Optional[list[str]] = None) -> List[BaseMessage]:
        lore_context = _load_cli_lorebook_raw(self.lore_loader, lore_tags)
        tag_hint = (
            f"当前注入设定标签（lore_tags）：{', '.join(lore_tags)}"
            if lore_tags
            else "当前注入：全部 lores md 原文"
        )
        system_instruction = f"""你是一个顶尖的网文创作Agent。
你的创作必须【严丝合缝】地符合以下百科设定的框架输出文本，不要 markdown 格式。

{lore_context}

【创作指令】：
- 逻辑严密，必须符合百科中的等级、人物、怪物设定背景。
- {tag_hint}

【多轮会话】：
- 用户可能续写下一章、改条件、或讨论设定；按本轮意图作答。
- 若要求输出正文，直接叙述，少客套；若仅问答设定，简明即可。
"""
        return [SystemMessage(content=system_instruction)]

    def chat_turn_stream(
        self, messages: List[BaseMessage], user_text: str
    ) -> Tuple[str, dict, bool]:
        """
        追加用户消息，流式调用模型，终端实时打印增量；最后把助手【正文】写入 messages
        （深度思考模型不把 reasoning_content 写入历史，避免多轮 400）。
        返回 (会话记录用展示文本, usage 摘要, 是否应写入会话文件；若 Ctrl+C 且无任何输出则为 False)。
        """
        messages.append(HumanMessage(content=user_text))
        last_usage: dict = {}
        interrupted = False
        reasoning_parts: list[str] = []
        content_parts: list[str] = []
        reasoning_header = False
        content_header = False

        try:
            if self._reasoner_mode:
                api_messages = convert_to_openai_messages(messages)
                stream = self._oai.chat.completions.create(
                    model=self.model_name,
                    messages=api_messages,
                    max_tokens=_REASONER_MAX_TOKENS,
                    stream=True,
                    stream_options={"include_usage": True},
                )
                for event in stream:
                    if getattr(event, "usage", None) is not None:
                        u = event.usage
                        last_usage = {
                            "total_tokens": getattr(u, "total_tokens", None),
                            "prompt_tokens": getattr(u, "prompt_tokens", None),
                            "completion_tokens": getattr(
                                u, "completion_tokens", None
                            ),
                        }
                    choices = getattr(event, "choices", None) or []
                    if not choices:
                        continue
                    delta = choices[0].delta
                    r_delta, c_delta = openai_chat_delta_reasoning_and_answer(delta)
                    if r_delta:
                        if not reasoning_header:
                            sys.stdout.write("\n── 深度思考 ──\n")
                            reasoning_header = True
                            sys.stdout.flush()
                        sys.stdout.write(r_delta)
                        sys.stdout.flush()
                        reasoning_parts.append(r_delta)
                    if c_delta:
                        if reasoning_header and not content_header:
                            sys.stdout.write("\n── 正文 ──\n")
                            content_header = True
                            sys.stdout.flush()
                        sys.stdout.write(c_delta)
                        sys.stdout.flush()
                        content_parts.append(c_delta)
            else:
                assert self.model is not None
                for chunk in self.model.stream(messages):
                    delta = parse_ai_chunk_text(chunk)
                    if delta:
                        sys.stdout.write(delta)
                        sys.stdout.flush()
                        content_parts.append(delta)
                    um = getattr(chunk, "usage_metadata", None) or {}
                    if um:
                        last_usage = um
        except KeyboardInterrupt:
            interrupted = True
            sys.stdout.write("\n")
            sys.stdout.flush()

        reasoning_text = "".join(reasoning_parts)
        content_text = "".join(content_parts)
        if reasoning_text.strip():
            display = f"【深度思考】\n{reasoning_text}\n\n【正文】\n{content_text}"
        else:
            display = content_text

        if interrupted and not display.strip():
            messages.pop()  # 无任何输出时撤销本轮 HumanMessage
            should_log = False
        else:
            messages.append(AIMessage(content=content_text))
            should_log = True
        if not interrupted:
            sys.stdout.write("\n")
            sys.stdout.flush()
        elif display.strip():
            sys.stdout.write("\n[本轮已中止，已保存已输出部分]\n")
            sys.stdout.flush()
        return display, last_usage, should_log


def _parse_tags(s: Optional[str]) -> Optional[list[str]]:
    if not s or not str(s).strip():
        return None
    return [t.strip() for t in str(s).split(",") if t.strip()]


def _append_turn_file(path: str, turn: int, user_text: str, assistant_text: str) -> None:
    sep = "\n" + "=" * 72 + "\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{sep}Turn {turn}\n[User]\n{user_text}\n\n[Assistant]\n{assistant_text}\n")


def _print_help() -> None:
    print(
        "命令：/help  /quit 或 /exit 退出并保存  /clear 清空对话（保留系统与 lore）\n"
        "默认深度思考模型：流式先显示「深度思考」再「正文」；历史里只保存正文。\n"
        "重新启动可加 --fast 使用对话模型（更快，无单独思考段）。\n"
        "生成中可按 Ctrl+C 中止本轮；会话记录仍会保存已输出部分。"
    )


if __name__ == "__main__":
    # 尽量避免 Windows 终端中文与流式乱码
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    parser = argparse.ArgumentParser(
        description="CLI 多轮对话：流式输出，退出时保存全文至 outputs/"
    )
    parser.add_argument(
        "task",
        nargs="?",
        default=None,
        help="可选：进入会话后自动作为第一条用户消息发送（否则直接等待输入）",
    )
    parser.add_argument(
        "--tags",
        metavar="T1,T2",
        help="逗号分隔的 lore tag；省略则注入全部 md",
    )
    parser.add_argument(
        "--list-tags",
        action="store_true",
        help="列出 lores 下全部 tag 后退出",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help=f"使用 {DEFAULT_CHAT_MODEL}（非深度思考），流式为单路正文",
    )
    args = parser.parse_args()

    loader = LoreLoader()
    if args.list_tags:
        for t in loader.get_lore_tags():
            print(t)
        sys.exit(0)

    tags = _parse_tags(args.tags)
    model_name = DEFAULT_CHAT_MODEL if args.fast else DEFAULT_REASONER_MODEL
    agent = WritingAgent(model_name=model_name)
    messages = agent.open_session(lore_tags=tags)

    os.makedirs("outputs", exist_ok=True)
    stamp = datetime.now().strftime("%m%d_%H%M%S")
    transcript_path = os.path.join("outputs", f"cli_session_{stamp}.txt")
    tags_line = ", ".join(tags) if tags else "(全部 md)"
    with open(transcript_path, "w", encoding="utf-8") as f:
        mode_note = (
            "深度思考（正文单独落盘于对话历史）"
            if agent._reasoner_mode
            else "对话模型"
        )
        f.write(
            f"# CLI 会话记录 {stamp}\n# lore: {tags_line}\n"
            f"# model: {agent.model_name} ({mode_note})\n"
            f"# 结束方式：/quit、Ctrl+C 或 Ctrl+D\n\n"
        )

    print(f"会话记录将写入：{transcript_path}")
    print(f"模型：{agent.model_name}（{'深度思考' if agent._reasoner_mode else '对话'}）")
    print("从 lores 已加载 md 原文。输入 /help 查看命令。\n")

    turn_counter = [0]

    def run_one_user_message(user_text: str) -> None:
        print("\n--- 流式输出 ---\n", flush=True)
        reply, meta, should_log = agent.chat_turn_stream(messages, user_text)
        tok = meta.get("total_tokens")
        if tok is not None:
            print(f"\n[本轮 total_tokens ≈ {tok}]", flush=True)
        if should_log:
            turn_counter[0] += 1
            _append_turn_file(transcript_path, turn_counter[0], user_text, reply)

    try:
        if args.task is not None and str(args.task).strip():
            run_one_user_message(str(args.task).strip())

        while True:
            try:
                line = input("\nYou> ")
            except EOFError:
                print("\n(EOF，结束会话)")
                break
            except KeyboardInterrupt:
                print("\n(中断输入，结束会话)")
                break

            raw = line.strip()
            if not raw:
                continue
            low = raw.lower()
            if low in ("/q", "/quit", "/exit"):
                break
            if low == "/help":
                _print_help()
                continue
            if low == "/clear":
                messages = agent.open_session(lore_tags=tags)
                print("已清空对话历史，系统与 lore 已重新加载。")
                continue

            run_one_user_message(raw)

    finally:
        print(f"\n会话已保存：{transcript_path}")
        if winsound is not None:
            try:
                winsound.Beep(1000, 300)
            except OSError:
                pass
