"""统一检索模块

提供多源检索能力：
- GraphRAG: 知识图谱社区检索
- BM25: 关键词精确匹配
- Vector: FAISS 语义相似度检索
- Fusion: RRF 结果融合
"""
from __future__ import annotations

from .repository import IndexRepository, load_index_repository
from .graphrag import GraphRAGRetriever
from .bm25 import BM25Retriever
from .vector import VectorRetriever
from .fusion import reciprocal_rank_fusion, weighted_rrf
from .multi_source import MultiSourceRetriever

__all__ = [
    "IndexRepository",
    "load_index_repository",
    "GraphRAGRetriever",
    "BM25Retriever",
    "VectorRetriever",
    "reciprocal_rank_fusion",
    "weighted_rrf",
    "MultiSourceRetriever",
]
