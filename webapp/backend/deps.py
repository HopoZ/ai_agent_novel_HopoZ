"""进程级单例：NovelAgent、命名日志。"""

import logging

from agents.novel import NovelAgent

logger = logging.getLogger("webapp.backend.server")

agent = NovelAgent()


def reset_agent_llm_cache() -> None:
    """API Key 在界面更新后，需丢弃已懒加载的模型实例。"""
    agent.model = None
