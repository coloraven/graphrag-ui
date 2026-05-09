"""结果融合算法 - RRF (Reciprocal Rank Fusion)"""
from __future__ import annotations

from collections import defaultdict

from ..schemas import Citation


def reciprocal_rank_fusion(
    source_lists: list[list[Citation]],
    limit: int = 7,
    k: int = 60,
) -> list[Citation]:
    """RRF 融合算法（等权重）

    Args:
        source_lists: 多个检索源的结果列表
        limit: 返回结果数量
        k: RRF 参数（默认 60）

    Returns:
        融合后的 Citation 列表
    """
    return weighted_rrf(source_lists, weights=None, limit=limit, k=k)


def weighted_rrf(
    source_lists: list[list[Citation]],
    weights: list[float] | None = None,
    limit: int = 7,
    k: int = 60,
) -> list[Citation]:
    """加权 RRF 融合算法

    Args:
        source_lists: 多个检索源的结果列表
        weights: 每个检索源的权重（None 表示等权重）
        limit: 返回结果数量
        k: RRF 参数（默认 60）

    Returns:
        融合后的 Citation 列表
    """
    if not source_lists:
        return []

    # 默认等权重
    if weights is None:
        weights = [1.0] * len(source_lists)

    scores: dict[str, float] = defaultdict(float)
    citation_map: dict[str, Citation] = {}

    for sources, weight in zip(source_lists, weights):
        for rank, citation in enumerate(sources, start=1):
            key = citation.source_id
            # 加权 RRF 公式：weight / (rank + k)
            scores[key] += weight / (rank + k)
            if key not in citation_map:
                citation_map[key] = citation

    # 按分数排序
    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    # 重新编号
    results = []
    for idx, source_id in enumerate(sorted_ids[:limit], start=1):
        citation = citation_map[source_id]
        # 创建新的 Citation 对象，更新 index
        results.append(
            Citation(
                index=idx,
                source_id=citation.source_id,
                document_name=citation.document_name,
                snippet=citation.snippet,
            )
        )

    return results
