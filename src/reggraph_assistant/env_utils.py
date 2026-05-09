"""环境变量管理工具

提供 GraphRAG 环境变量隔离和覆盖功能
"""
from __future__ import annotations

from contextlib import contextmanager
import os
from threading import Lock
from typing import Iterator

from .settings import Settings


_ENV_LOCK = Lock()


def build_env_overrides(settings: Settings) -> dict[str, str]:
    """构建 GraphRAG 环境变量覆盖

    Args:
        settings: 应用配置

    Returns:
        环境变量字典
    """
    return {
        "GRAPHRAG_API_KEY": settings.llm.api_key,
        "GRAPHRAG_API_KEY_EMBEDDING": settings.embedding.api_key,
        "GRAPHRAG_LLM_MODEL": settings.llm.model,
        "GRAPHRAG_EMBEDDING_MODEL": settings.embedding.model,
        "GRAPHRAG_API_BASE": settings.llm.api_base,
        "GRAPHRAG_API_BASE_EMBEDDING": settings.embedding.api_base,
        "API_BASE": settings.llm.api_base,
        "API_BASE_EMBEDDING": settings.embedding.api_base,
    }


@contextmanager
def isolated_graphrag_env(overrides: dict[str, str]) -> Iterator[None]:
    """临时设置环境变量的上下文管理器

    Args:
        overrides: 要覆盖的环境变量字典

    Yields:
        None

    Example:
        >>> with isolated_graphrag_env({"API_KEY": "test"}):
        ...     # 在此作用域内环境变量被覆盖
        ...     pass
    """
    with _ENV_LOCK:
        old_env = {}
        for key, value in overrides.items():
            old_env[key] = os.environ.get(key)
            os.environ[key] = value

        try:
            yield
        finally:
            for key, old_value in old_env.items():
                if old_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = old_value
