"""Agent 基类

提供统一的 Agent 接口和共享功能
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..llm_client import LLMClient
from ..settings import Settings


class BaseAgent(ABC):
    """Agent 基类

    所有 Agent 都应继承此基类，提供统一的接口和共享功能
    """

    def __init__(self, settings: Settings):
        """初始化 Agent

        Args:
            settings: 应用配置
        """
        self.settings = settings
        self._llm_client: LLMClient | None = None

    @property
    def llm_client(self) -> LLMClient:
        """延迟初始化的 LLM 客户端

        Returns:
            LLMClient 实例
        """
        if self._llm_client is None:
            self._llm_client = LLMClient(self.settings)
        return self._llm_client

    @abstractmethod
    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """执行 Agent 逻辑

        Args:
            state: 输入状态

        Returns:
            输出状态
        """
        pass
