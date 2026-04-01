"""Flet：API Key、可选 lore 标签、DeepSeek 流式多轮对话。桌面调试：python src/main.py；APK：在 mobile 目录执行 flet build apk。"""

from __future__ import annotations

import asyncio

import flet as ft
import httpx

from lore_mobile import (
    clear_imported_lores,
    import_md_from_directory,
    import_picked_md_files,
    load_lorebook_raw,
    lore_display_source,
    resolve_lores_dir,
)
from stream_client import stream_chat_async

STORAGE_KEY = "deepseek_api_key"


def _parse_tags(s: str) -> list[str] | None:
    s = (s or "").strip()
    if not s:
        return None
    return [t.strip() for t in s.split(",") if t.strip()]


def _system_prompt(lore_body: str, tag_hint: str) -> str:
    if not (lore_body or "").strip():
        lore_block = "（当前未加载百科设定文件；请作为通用网文创作助手作答。）"
    else:
        lore_block = lore_body
    return f"""你是一个顶尖的网文创作Agent。
你的创作必须【严丝合缝】地符合以下百科设定的框架。

{lore_block}

【创作指令】：
- 逻辑严密，必须符合百科中的等级、人物、怪物设定背景。
- {tag_hint}

【多轮会话】：
- 用户可能续写下一章、改条件、或讨论设定；按本轮意图作答。
- 若要求输出正文，直接叙述，少客套；若仅问答设定，简明即可。
"""


async def main(page: ft.Page) -> None:
    page.title = "NovelH 对话"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 12

    api_field = ft.TextField(
        label="DeepSeek API Key",
        password=True,
        can_reveal_password=True,
        expand=True,
        autocorrect=False,
        enable_suggestions=False,
    )
    tags_field = ft.TextField(
        label="Lore 标签（可选，逗号分隔；留空=全部 md）",
        expand=True,
        autocorrect=False,
    )
    status_text = ft.Text("", size=12, color=ft.Colors.GREY_700)

    api_messages: list[dict[str, str]] = []

    chat_col = ft.Column(
        spacing=8,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    input_field = ft.TextField(
        hint_text="输入消息后发送…",
        multiline=True,
        min_lines=2,
        max_lines=6,
        expand=True,
    )

    send_btn = ft.FilledButton("发送", icon=ft.Icons.SEND)
    stop_btn = ft.OutlinedButton("停止", icon=ft.Icons.STOP, visible=False)

    stream_cancel: asyncio.Event | None = None

    def _snack(msg: str) -> None:
        page.snack_bar = ft.SnackBar(ft.Text(msg))
        page.snack_bar.open = True
        page.update()

    def _rebuild_session() -> None:
        tags = _parse_tags(tags_field.value or "")
        data_path = resolve_lores_dir()
        lore_body, hint = load_lorebook_raw(tags)
        src = lore_display_source(data_path)
        if lore_body:
            status_text.value = f"设定来源：{src} ｜ {data_path} ｜ {hint}"
        else:
            status_text.value = f"{hint}（来源：{src}）"
        api_messages.clear()
        api_messages.append({"role": "system", "content": _system_prompt(lore_body, hint)})
        chat_col.controls.clear()
        page.update()

    async def save_key_async(_: ft.ControlEvent | None = None) -> None:
        v = (api_field.value or "").strip()
        if hasattr(page.client_storage, "set_async"):
            await page.client_storage.set_async(STORAGE_KEY, v)
        else:
            page.client_storage.set(STORAGE_KEY, v)
        _snack("API Key 已保存到本机")

    def save_key_sync(_: ft.ControlEvent) -> None:
        asyncio.create_task(save_key_async())

    def new_session(_: ft.ControlEvent) -> None:
        _rebuild_session()
        _snack("已按当前标签重新加载设定与对话")

    async def load_stored_key() -> None:
        if hasattr(page.client_storage, "get_async"):
            v = await page.client_storage.get_async(STORAGE_KEY)
        else:
            v = page.client_storage.get(STORAGE_KEY)
        if v:
            api_field.value = str(v)

    async def do_send(_: ft.ControlEvent | None = None) -> None:
        nonlocal stream_cancel
        key = (api_field.value or "").strip()
        if not key:
            _snack("请先填写并保存 API Key")
            return
        user_text = (input_field.value or "").strip()
        if not user_text:
            return

        input_field.value = ""
        page.update()

        chat_col.controls.append(
            ft.Container(
                content=ft.Text(f"You：{user_text}", selectable=True),
                padding=8,
                bgcolor=ft.Colors.BLUE_50,
                border_radius=8,
            )
        )
        assistant_text = ft.Text("", selectable=True)
        assistant_wrap = ft.Container(
            content=assistant_text,
            padding=8,
            bgcolor=ft.Colors.GREEN_50,
            border_radius=8,
        )
        chat_col.controls.append(assistant_wrap)
        page.update()

        api_messages.append({"role": "user", "content": user_text})
        send_btn.disabled = True
        stop_btn.visible = True
        stream_cancel = asyncio.Event()
        page.update()

        full: list[str] = []
        try:
            async for delta in stream_chat_async(api_messages, key):
                if stream_cancel and stream_cancel.is_set():
                    break
                full.append(delta)
                assistant_text.value = "".join(full)
                page.update()

            reply = "".join(full)
            if reply.strip():
                api_messages.append({"role": "assistant", "content": reply})
        except httpx.HTTPStatusError as e:
            _snack(f"HTTP 错误：{e.response.status_code}")
            if not full and api_messages and api_messages[-1].get("role") == "user":
                api_messages.pop()
        except Exception as ex:  # noqa: BLE001
            _snack(str(ex) or type(ex).__name__)
            if not full and api_messages and api_messages[-1].get("role") == "user":
                api_messages.pop()
        finally:
            send_btn.disabled = False
            stop_btn.visible = False
            stream_cancel = None
            page.update()

    def on_stop(_: ft.ControlEvent) -> None:
        nonlocal stream_cancel
        if stream_cancel:
            stream_cancel.set()

    send_btn.on_click = lambda e: asyncio.create_task(do_send())
    stop_btn.on_click = on_stop

    async def import_md_files_click(_: ft.ControlEvent) -> None:
        files = await ft.FilePicker().pick_files(
            dialog_title="选择设定 .md 文件（可多选）",
            allow_multiple=True,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["md"],
            with_data=True,
        )
        if not files:
            return
        items: list[tuple[str, bytes | None, str | None]] = []
        for f in files:
            p = getattr(f, "path", None)
            items.append((f.name, f.bytes, str(p) if p else None))
        n, err = import_picked_md_files(items)
        if err:
            _snack(f"已导入 {n} 个文件；部分失败：{err[:200]}")
        else:
            _snack(f"已导入 {n} 个 .md，已写入本应用目录")
        _rebuild_session()

    async def import_folder_click(_: ft.ControlEvent) -> None:
        path = await ft.FilePicker().get_directory_path(
            dialog_title="选择包含 .md 的设定文件夹（保留子目录作为 tag）",
        )
        if not path:
            return
        n = import_md_from_directory(path)
        _snack(f"已从文件夹导入 {n} 个 .md")
        _rebuild_session()

    def clear_import_click(_: ft.ControlEvent) -> None:
        clear_imported_lores()
        _rebuild_session()
        _snack("已清空「用户导入」的设定文件")

    await load_stored_key()
    _rebuild_session()

    import_files_btn = ft.FilledButton(
        "导入 .md",
        icon=ft.Icons.UPLOAD_FILE,
        on_click=import_md_files_click,
    )
    import_dir_btn = ft.FilledButton(
        "导入文件夹",
        icon=ft.Icons.FOLDER_OPEN,
        on_click=import_folder_click,
        disabled=page.web,
    )
    clear_import_btn = ft.OutlinedButton(
        "清空导入",
        icon=ft.Icons.DELETE_OUTLINE,
        on_click=clear_import_click,
    )

    page.add(
        ft.Text(
            "DeepSeek deepseek-chat；API Key 与导入的设定保存在本机应用目录（不上传服务器）。",
            size=12,
        ),
        ft.Row(
            controls=[
                api_field,
                ft.FilledButton("保存密钥", icon=ft.Icons.SAVE, on_click=save_key_sync),
            ],
        ),
        ft.Row(
            controls=[import_files_btn, import_dir_btn, clear_import_btn],
            wrap=True,
        ),
        ft.Row(
            controls=[
                tags_field,
                ft.FilledButton("新开会话", icon=ft.Icons.REFRESH, on_click=new_session),
            ],
        ),
        status_text,
        ft.Divider(),
        ft.Container(
            content=chat_col,
            expand=True,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=8,
            padding=8,
        ),
        ft.Row(
            controls=[input_field, send_btn, stop_btn],
            vertical_alignment=ft.CrossAxisAlignment.END,
        ),
    )


if __name__ == "__main__":
    ft.app(main)
