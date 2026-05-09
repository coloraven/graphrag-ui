"""GraphRAG 检索器"""
from __future__ import annotations

import asyncio
from contextlib import redirect_stdout, redirect_stderr
import io
import logging
import re
from typing import TYPE_CHECKING

import pandas as pd
from graphrag.cli.query import run_local_search

from ..env_utils import build_env_overrides, isolated_graphrag_env
from ..schemas import Citation
from .repository import IndexRepository

if TYPE_CHECKING:
    from ..settings import Settings

logger = logging.getLogger(__name__)

# 预编译正则表达式
INTERNAL_DATA_REFERENCE_PATTERN = re.compile(r"\s*\[Data:[^\]]+\]", re.IGNORECASE)
EMPTY_PLACEHOLDER_LINE_PATTERN = re.compile(r"^\s*[-—]{2,}\s*[：:]\s*[-—]{2,}\s*$", re.MULTILINE)
SPACED_BOLD_PATTERN = re.compile(r"\*\*\s+([^*\n]+?)\s+\*\*")
SPACE_BEFORE_PUNCTUATION_PATTERN = re.compile(r"\s+([，。；：,.!?！？])")


def clean_model_answer(answer: str) -> str:
    """清理模型生成的答案，移除内部引用和格式问题"""
    text = str(answer or "")
    text = INTERNAL_DATA_REFERENCE_PATTERN.sub("", text)
    text = EMPTY_PLACEHOLDER_LINE_PATTERN.sub("", text)
    text = SPACED_BOLD_PATTERN.sub(lambda match: f"**{match.group(1).strip()}**", text)
    text = SPACE_BEFORE_PUNCTUATION_PATTERN.sub(r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class GraphRAGRetriever:
    """GraphRAG 检索器 - 基于知识图谱的社区检索"""

    def __init__(self, settings: Settings, index_repository: IndexRepository):
        self.settings = settings
        self.index_repository = index_repository

    async def retrieve(self, query: str, limit: int = 5) -> tuple[str, list[Citation]]:
        """执行 GraphRAG 检索

        Args:
            query: 查询字符串
            limit: 返回结果数量

        Returns:
            (answer, citations) 元组
        """
        # 异步执行 GraphRAG 搜索
        response, context_data = await self._run_search_async(query, "Markdown")

        # 提取引用
        citations = self._extract_citations(context_data, limit)

        # 清理答案
        answer = clean_model_answer(str(response))

        return answer, citations

    async def _run_search_async(self, query: str, response_type: str) -> tuple[object, object]:
        """异步执行 GraphRAG 搜索"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._run_search_sync,
            query,
            response_type,
        )

    def _run_search_sync(self, query: str, response_type: str) -> tuple[object, object]:
        """同步执行 GraphRAG 搜索（在 executor 中运行）"""
        overrides = build_env_overrides(self.settings)

        with isolated_graphrag_env(overrides):
            try:
                # 重定向标准输出和标准错误以抑制 GraphRAG 的打印输出
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    return run_local_search(
                        data_dir=self.settings.paths.index_dir,
                        root_dir=self.settings.paths.graphrag_project_dir,
                        community_level=2,
                        response_type=response_type,
                        streaming=False,
                        query=query,
                        verbose=False,
                    )
            except Exception as e:
                logger.error(f"GraphRAG local search failed: {e}")
                raise

    def _extract_citations(self, context_data: dict | object, limit: int) -> list[Citation]:
        """从 GraphRAG 上下文数据中提取引用"""
        if not isinstance(context_data, dict):
            return []

        sources_df = context_data.get("sources")
        if not isinstance(sources_df, pd.DataFrame) or sources_df.empty:
            return []

        document_lookup = self.index_repository.document_lookup()
        citations: list[Citation] = []

        for index, (_, row) in enumerate(sources_df.head(limit).iterrows(), start=1):
            snippet = str(row.get("text") or "").strip()
            source_id = str(row.get("id") or "")
            if not snippet:
                continue

            document_name = document_lookup.get(
                source_id,
                document_lookup.get(source_id.removeprefix("T"), "未知来源")
            )

            citations.append(
                Citation(
                    index=index,
                    source_id=source_id,
                    document_name=document_name,
                    snippet=snippet[:500],
                )
            )

        return citations
