"""PyInstaller 入口：启动 FastAPI（与 electron 子进程环境变量配合）。"""

from __future__ import annotations

import os
import sys


def _bootstrap_pyinstaller_cwd() -> None:
    """
    单文件 exe 由 Electron 启动时 cwd 常为 resources/backend，而打包的静态资源在 _MEIPASS 下。
    不切换目录会导致 webapp/static、webapp/frontend/dist 等相对路径不存在，进程立刻退出。
    """
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", None)
        if base:
            os.chdir(base)


def main() -> None:
    _bootstrap_pyinstaller_cwd()
    import uvicorn

    os.environ.setdefault("SKIP_FRONTEND_BUILD", "1")
    port = int(os.environ.get("NOVEL_AGENT_PORT", "8000"))
    uvicorn.run(
        "webapp.backend.server:app",
        host="127.0.0.1",
        port=port,
        factory=False,
    )


if __name__ == "__main__":
    main()
