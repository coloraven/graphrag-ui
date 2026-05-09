"""多源检索器 - 统一入口"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from ..schemas import Citation
from .repository import IndexRepository, load_index_repository
from .graphrag import GraphRAGRetriever
from .bm25 import BM25Retriever
from .vector import VectorRetriever
from .fusion import weighted_rrf

if TYPE_CHECKING:
    from ..settings import Settings

logger = logging.getLogger(__name__)


class MultiSourceRetriever:
    """多源检索器 - 统一管理 GraphRAG + BM25 + Vector 三路检索

    职责：
    1. 初始化三个检索器
    2. 并行执行三路检索
    3. 融合结果（RRF）
    4. 提供统一的检索接口
    """

    def __init__(self, settings: Settings):
        self.settings = settings

        # 初始化索引仓库（共享）
        self.index_repository = load_index_repository(settings)

        # 初始化三个检索器
        self.graphrag_retriever = GraphRAGRetriever(settings, self.index_repository)
        self.bm25_retriever = BM25Retriever.get_or_create(
            self.index_repository,
            cache_key=str(settings.paths.index_dir),
        )
        self.vector_retriever = VectorRetriever(settings, self.index_repository)

    async def retrieve(
        self,
        query: str,
        query_variants: list[str] | None = None,
        sources: list[str] | None = None,
        fusion_method: str = "rrf",
        intent: str = "policy_answer",
        limit: int = 7,
        timeout: float = 30.0,
    ) -> dict[str, list[Citation]]:
        """执行多源检索

        Args:
            query: 查询字符串
            query_variants: 查询变体列表（用于 BM25）
            sources: 启用的检索源列表，None 表示全部启用
            fusion_method: 融合方法（"rrf" 或 "concat"）
            intent: 用户意图（用于自适应权重）
            limit: 返回结果数量
            timeout: 检索超时时间（秒）

        Returns:
            包含各路检索结果和融合结果的字典
        """
        # 默认启用所有检索源
        if sources is None:
            sources = ["graphrag", "bm25", "vector"]

        query_variants = query_variants or [query]

        # 并行执行三路检索（带超时保护）
        tasks = []
        if "graphrag" in sources:
            tasks.append(self._graphrag_retrieve(query))
        else:
            tasks.append(asyncio.sleep(0, result=[]))

        if "bm25" in sources:
            tasks.append(self._bm25_retrieve(query_variants))
        else:
            tasks.append(asyncio.sleep(0, result=[]))

        if "vector" in sources:
            tasks.append(self._vector_retrieve(query))
        else:
            tasks.append(asyncio.sleep(0, result=[]))

        try:
            graphrag_sources, bm25_sources, vector_sources = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout
            )

            # 处理异常结果
            if isinstance(graphrag_sources, Exception):
                logger.error(f"GraphRAG retrieval failed: {graphrag_sources}")
                graphrag_sources = []
            if isinstance(bm25_sources, Exception):
                logger.error(f"BM25 retrieval failed: {bm25_sources}")
                bm25_sources = []
            if isinstance(vector_sources, Exception):
                logger.error(f"Vector retrieval failed: {vector_sources}")
                vector_sources = []

        except asyncio.TimeoutError:
            logger.error(f"Retrieval timeout after {timeout}s, using partial results")
            graphrag_sources, bm25_sources, vector_sources = [], [], []

        # 融合结果
        fused_sources = self._fuse_sources(
            graphrag_sources,
            bm25_sources,
            vector_sources,
            method=fusion_method,
            intent=intent,
            limit=limit,
        )

        return {
            "graphrag_sources": graphrag_sources,
            "bm25_sources": bm25_sources,
            "vector_sources": vector_sources,
            "fused_sources": fused_sources,
        }

    async def _graphrag_retrieve(self, query: str) -> list[Citation]:
        """GraphRAG 检索"""
        try:
            _, citations = await self.graphrag_retriever.retrieve(query, limit=5)
            return citations
        except Exception as e:
            logger.error(f"GraphRAG retrieval failed: {e}")
            return []

    async def _bm25_retrieve(self, query_variants: list[str]) -> list[Citation]:
        """BM25 检索（支持查询变体）"""
        try:
            from .fusion import reciprocal_rank_fusion

            # 对每个查询变体执行检索
            all_sources: list[list[Citation]] = []
            for variant in query_variants[:3]:  # 最多使用 3 个变体
                sources = await asyncio.to_thread(
                    self.bm25_retriever.retrieve,
                    variant,
                    4
                )
                if sources:
                    all_sources.append(sources)

            # 融合多个变体的结果
            return reciprocal_rank_fusion(all_sources, limit=5) if all_sources else []

        except Exception as e:
            logger.error(f"BM25 retrieval failed: {e}")
            return []

    async def _vector_retrieve(self, query: str) -> list[Citation]:
        """向量检索"""
        try:
            return await self.vector_retriever.retrieve(query, limit=5)
        except Exception as e:
            logger.error(f"Vector retrieval failed: {e}")
            return []

    def _fuse_sources(
        self,
        graphrag_sources: list[Citation],
        bm25_sources: list[Citation],
        vector_sources: list[Citation],
        method: str = "rrf",
        intent: str = "policy_answer",
        limit: int = 7,
    ) -> list[Citation]:
        """融合多源检索结果（支持自适应权重）"""
        if method == "rrf":
            # 根据意图动态调整权重
            if intent == "checklist":
                # 材料清单场景：GraphRAG 权重更高（关注流程和关系）
                weights = [0.5, 0.3, 0.2]  # GraphRAG, BM25, Vector
            else:
                # 政策咨询场景：Vector 权重更高（关注语义理解）
                weights = [0.3, 0.2, 0.5]  # GraphRAG, BM25, Vector

            return weighted_rrf(
                [graphrag_sources, bm25_sources, vector_sources],
                weights=weights,
                limit=limit,
            )

        # concat 方法：简单拼接
        return (graphrag_sources + bm25_sources + vector_sources)[:limit]
