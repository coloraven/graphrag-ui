"""Retriever Agent - 多源检索执行"""
from __future__ import annotations

from typing import Any

from .base import BaseAgent
from .state_types import RetrieverState
from ..schemas import Citation
from ..settings import Settings


class RetrieverAgent(BaseAgent):
    """检索 Agent - 负责多源并行检索和结果融合

    使用统一的 MultiSourceRetriever 简化检索逻辑
    """

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """执行检索逻辑（同步接口，实际调用异步方法）

        Args:
            state: 输入状态

        Returns:
            输出状态
        """
        import asyncio
        return asyncio.run(self.retrieve(
            query=state["query"],
            query_variants=state["query_variants"],
            retrieval_plan=state.get("retrieval_plan"),
        ))

    async def retrieve(
        self,
        query: str,
        query_variants: list[str],
        retrieval_plan: dict | None = None,
        timeout: float = 30.0,
    ) -> RetrieverState:
        """执行三路并行检索（异步版本）

        使用 MultiSourceRetriever 统一管理三路检索：
        1. GraphRAG 检索（知识图谱社区检索）
        2. BM25 检索（关键词精确匹配）
        3. Vector 检索（FAISS 语义相似度）
        4. RRF 融合多源结果

        Args:
            query: 查询字符串
            query_variants: 查询变体列表
            retrieval_plan: 检索计划（可选，用于指定融合方法）
            timeout: 检索超时时间（秒），默认 30 秒

        Returns:
            RetrieverState: 包含各路检索结果和融合结果
        """
        from ..retrieval import MultiSourceRetriever

        # 使用统一的多源检索器
        retriever = MultiSourceRetriever(self.settings)

        # 提取检索参数
        fusion_method = (retrieval_plan or {}).get("fusion_method", "rrf")
        intent = (retrieval_plan or {}).get("intent", "policy_answer")

        # 执行检索
        results = await retriever.retrieve(
            query=query,
            query_variants=query_variants,
            fusion_method=fusion_method,
            intent=intent,
            limit=7,
            timeout=timeout,
        )

        # 构建返回状态
        return RetrieverState(
            query=query,
            query_variants=query_variants,
            graphrag_sources=results["graphrag_sources"],
            bm25_sources=results["bm25_sources"],
            vector_sources=results["vector_sources"],
            fused_sources=results["fused_sources"],
        )
