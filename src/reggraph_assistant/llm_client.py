"""统一的 LLM 客户端

提供统一的 LLM API 调用接口，支持重试、超时、错误处理
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from .settings import Settings


logger = logging.getLogger(__name__)


class LLMClient:
    """LLM 客户端

    统一管理 LLM API 调用，提供重试、超时、错误处理等功能
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.api_base = settings.llm.api_base
        self.api_key = settings.llm.api_key
        self.model = settings.llm.model

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> str:
        """异步聊天补全

        Args:
            messages: 消息列表，格式 [{"role": "user", "content": "..."}]
            temperature: 温度参数（0-1）
            max_tokens: 最大生成 token 数
            timeout: 超时时间（秒）
            max_retries: 最大重试次数

        Returns:
            生成的文本内容

        Raises:
            httpx.HTTPError: HTTP 请求失败
            ValueError: API 返回格式错误
        """
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        last_error = None
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(
                        f"{self.api_base}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()

                    # 提取生成内容
                    if "choices" not in data or not data["choices"]:
                        raise ValueError("API response missing 'choices' field")

                    content = data["choices"][0]["message"]["content"]
                    return content.strip()

            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(f"LLM API timeout (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    continue
            except httpx.HTTPStatusError as e:
                last_error = e
                logger.error(f"LLM API HTTP error (attempt {attempt + 1}/{max_retries}): {e.response.status_code}")
                if attempt < max_retries - 1 and e.response.status_code >= 500:
                    continue
                raise
            except (httpx.RequestError, ValueError) as e:
                last_error = e
                logger.error(f"LLM API request error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    continue

        # 所有重试都失败
        raise RuntimeError(f"LLM API call failed after {max_retries} attempts") from last_error

    def chat_completion_sync(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> str:
        """同步聊天补全

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大生成 token 数
            timeout: 超时时间（秒）
            max_retries: 最大重试次数

        Returns:
            生成的文本内容
        """
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        last_error = None
        for attempt in range(max_retries):
            try:
                with httpx.Client(timeout=timeout) as client:
                    response = client.post(
                        f"{self.api_base}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()

                    if "choices" not in data or not data["choices"]:
                        raise ValueError("API response missing 'choices' field")

                    content = data["choices"][0]["message"]["content"]
                    return content.strip()

            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(f"LLM API timeout (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    continue
            except httpx.HTTPStatusError as e:
                last_error = e
                logger.error(f"LLM API HTTP error (attempt {attempt + 1}/{max_retries}): {e.response.status_code}")
                if attempt < max_retries - 1 and e.response.status_code >= 500:
                    continue
                raise
            except (httpx.RequestError, ValueError) as e:
                last_error = e
                logger.error(f"LLM API request error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    continue

        raise RuntimeError(f"LLM API call failed after {max_retries} attempts") from last_error
