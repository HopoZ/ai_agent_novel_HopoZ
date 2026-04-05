"""
磁盘持久化：单本小说 `novel.db`（SQLite）。

- `novel_sqlite.py`：Schema、四表与章节行级存储。
- `storage.py`：`NovelState`、章节记录的读写入口。
- `graph_tables.py`：图谱同步、`persist_chapter_artifacts` 等。
"""
