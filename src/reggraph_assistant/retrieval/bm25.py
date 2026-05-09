"""BM25 检索器"""
from __future__ import annotations

from collections import Counter
from math import log
from typing import ClassVar

from ..schemas import Citation
from ..text_utils import tokenize
from .repository import IndexRepository, TextUnitRecord


class BM25Retriever:
    """BM25 检索器 - 基于关键词的精确匹配

    使用预计算的 token_counts 缓存，避免重复分词
    """

    # 类级别缓存（所有实例共享）
    _cache: ClassVar[dict[str, BM25Retriever]] = {}

    def __init__(self, index_repository: IndexRepository, cache_key: str):
        """初始化 BM25 检索器

        Args:
            index_repository: 索引仓库
            cache_key: 缓存键（通常是索引目录路径）
        """
        self.cache_key = cache_key
        self.documents: list[tuple[str, str, str, Counter[str], int]] = []
        self.document_frequency: Counter[str] = Counter()

        # 预计算所有文档的 token_counts
        text_units = index_repository.text_units()
        for record in text_units:
            token_counts = Counter(tokenize(record.text))
            if not token_counts:
                continue

            doc_length = sum(token_counts.values())
            self.documents.append((
                record.source_id,
                record.document_name,
                record.text,
                token_counts,
                doc_length
            ))
            self.document_frequency.update(token_counts.keys())

        # 计算平均文档长度
        self.avg_doc_length = (
            sum(doc_length for *_, doc_length in self.documents) / len(self.documents)
            if self.documents else 0
        )

    @classmethod
    def get_or_create(cls, index_repository: IndexRepository, cache_key: str) -> BM25Retriever:
        """获取或创建 BM25 检索器（带缓存）

        Args:
            index_repository: 索引仓库
            cache_key: 缓存键

        Returns:
            BM25Retriever 实例
        """
        if cache_key not in cls._cache:
            cls._cache[cache_key] = cls(index_repository, cache_key)
        return cls._cache[cache_key]

    @classmethod
    def clear_cache(cls, cache_key: str | None = None) -> None:
        """清除缓存

        Args:
            cache_key: 要清除的缓存键，None 表示清除所有
        """
        if cache_key is None:
            cls._cache.clear()
        else:
            cls._cache.pop(cache_key, None)

    def retrieve(self, query: str, limit: int = 4) -> list[Citation]:
        """执行 BM25 检索

        Args:
            query: 查询字符串
            limit: 返回结果数量

        Returns:
            按相关性排序的 Citation 列表
        """
        query_tokens = Counter(tokenize(query))
        if not query_tokens or not self.documents:
            return []

        scored: list[tuple[float, str, str, str]] = []

        # 使用预计算的 token_counts
        for source_id, document_name, text, token_counts, doc_length in self.documents:
            score = 0.0
            for token, query_weight in query_tokens.items():
                frequency = token_counts.get(token, 0)
                if frequency == 0:
                    continue

                # BM25 公式
                idf = log(1 + (len(self.documents) - self.document_frequency[token] + 0.5) / (self.document_frequency[token] + 0.5))
                denominator = frequency + 1.2 * (1 - 0.75 + 0.75 * doc_length / self.avg_doc_length)
                score += query_weight * idf * (frequency * 2.2 / denominator)

            if score > 0:
                scored.append((score, source_id, document_name, text))

        # 按分数排序并返回
        citations: list[Citation] = []
        for idx, (_, source_id, document_name, text) in enumerate(sorted(scored, key=lambda item: item[0], reverse=True)[:limit], start=1):
            citations.append(
                Citation(
                    index=idx,
                    source_id=source_id,
                    document_name=document_name,
                    snippet=text[:500],
                )
            )
        return citations
