from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from math import log
import re

from .citation_audit import normalize_citation_indices
from .retrieval import IndexRepository, load_index_repository
from .retrieval.fusion import reciprocal_rank_fusion
from .schemas import Citation, EvidenceFact, EvidencePack, RiskFlag
from .settings import Settings
from .text_utils import tokenize
SCENARIO_KEYWORDS = (
    "公司登记",
    "企业登记",
    "营业执照",
    "经营范围",
    "个体工商户",
    "设立登记",
    "变更登记",
    "注销登记",
    "线上办理",
    "线下窗口",
    "办理材料",
    "办理时限",
    "咨询答复",
)
DOMAIN_EXPANSIONS = {
    "材料": ("申请材料", "材料清单", "材料核验"),
    "办理": ("办理流程", "办理渠道", "办理时限"),
    "依据": ("政策依据", "公开口径", "资料依据"),
    "经营范围": ("经营范围登记", "许可经营项目", "一般经营项目"),
    "营业执照": ("营业执照事项", "营业执照变更", "营业执照领取"),
}
RRF_K = 60


def _source_key(source: Citation) -> str:
    return source.source_id or f"{source.document_name}:{source.snippet[:80]}"


def build_query_variants(query: str, scenario_tags: list[str] | None = None, max_variants: int = 5) -> list[str]:
    normalized_query = " ".join(query.split())
    variants: list[str] = [normalized_query] if normalized_query else []
    tags = scenario_tags or extract_scenario_tags(query)

    if tags:
        variants.append(" ".join([normalized_query, *tags]).strip())

    for keyword, expansions in DOMAIN_EXPANSIONS.items():
        if keyword not in query:
            continue
        for expansion in expansions:
            variants.append(" ".join([normalized_query, expansion]).strip())

    deduped: list[str] = []
    for variant in variants:
        if variant and variant not in deduped:
            deduped.append(variant)
        if len(deduped) >= max_variants:
            break
    return deduped
def retrieve_keyword_sources(
    query: str,
    settings: Settings,
    limit: int = 4,
    index_repository: IndexRepository | None = None,
) -> list[Citation]:
    """使用 BM25 检索关键词来源（带缓存优化）

    Args:
        query: 查询字符串
        settings: 应用配置
        limit: 返回结果数量
        index_repository: 索引仓库（可选）

    Returns:
        按相关性排序的 Citation 列表
    """
    from .retrieval.bm25 import BM25Retriever

    repository = index_repository or load_index_repository(settings.paths.index_dir)

    # 使用缓存的 BM25 检索器
    cache_key = str(settings.paths.index_dir)
    bm25_retriever = BM25Retriever.get_or_create(repository, cache_key)

    return bm25_retriever.retrieve(query, limit=limit)


def rerank_sources(query: str, query_variants: list[str], sources: list[Citation], scenario_tags: list[str], limit: int = 5) -> list[Citation]:
    query_tokens = Counter(tokenize("\n".join([query, *query_variants])))
    if not query_tokens:
        return normalize_citation_indices(sources[:limit])

    scored: list[tuple[float, int, Citation]] = []
    for original_rank, source in enumerate(sources, start=1):
        snippet_tokens = Counter(tokenize(source.snippet))
        overlap = sum(min(query_tokens[token], snippet_tokens.get(token, 0)) for token in query_tokens)
        coverage = overlap / max(len(query_tokens), 1)
        scenario_boost = 0.08 * sum(1 for tag in scenario_tags if tag and tag in source.snippet)
        source_order_boost = 1 / (RRF_K + original_rank)
        scored.append((coverage + scenario_boost + source_order_boost, original_rank, source))

    ordered = [source for _score, _rank, source in sorted(scored, key=lambda item: (-item[0], item[1]))[:limit]]
    return normalize_citation_indices(ordered)


def hybrid_retrieve_sources(
    query: str,
    settings: Settings,
    primary_sources: list[Citation],
    scenario_tags: list[str],
    query_variants: list[str] | None = None,
    limit: int = 5,
) -> tuple[list[Citation], list[str]]:
    variants = query_variants or build_query_variants(query, scenario_tags)
    index_repository = load_index_repository(settings.paths.index_dir)
    keyword_ranked_lists = [
        retrieve_keyword_sources(variant, settings, limit=limit, index_repository=index_repository)
        for variant in variants
    ]
    primary = normalize_citation_indices(primary_sources)
    fused = reciprocal_rank_fusion([primary, *keyword_ranked_lists], limit=limit)
    reranked = rerank_sources(query, variants, fused, scenario_tags, limit=limit)
    return merge_sources(primary, reranked, limit=limit), variants


def extract_scenario_tags(query: str, snippets: list[str] | None = None) -> list[str]:
    haystack = "\n".join([query, *(snippets or [])])
    return [keyword for keyword in SCENARIO_KEYWORDS if keyword in haystack]


def merge_sources(primary: list[Citation], supplemental: list[Citation], limit: int = 7) -> list[Citation]:
    seen: set[str] = set()
    merged: list[Citation] = []
    for source in [*primary, *supplemental]:
        key = source.source_id or f"{source.document_name}:{source.snippet[:60]}"
        if key in seen:
            continue
        seen.add(key)
        merged.append(source)
        if len(merged) >= limit:
            break
    return normalize_citation_indices(merged)


def build_evidence_pack(
    query: str,
    intent: str,
    sources: list[Citation],
    scenario_tags: list[str],
    query_variants: list[str] | None = None,
) -> EvidencePack:
    normalized_sources = normalize_citation_indices(sources)
    snippets = [source.snippet for source in normalized_sources]
    tags = scenario_tags or extract_scenario_tags(query, snippets)
    key_facts = [
        EvidenceFact(
            title=f"依据 {source.index}：{source.document_name}",
            detail=source.snippet[:180],
            source_indices=[source.index],
        )
        for source in normalized_sources[:4]
    ]

    risks: list[RiskFlag] = []
    if not normalized_sources:
        risks.append(RiskFlag(level="warning", message="当前知识库未返回可用依据片段，答复需要人工复核。"))
    if "经营范围" in tags:
        risks.append(RiskFlag(level="warning", message="涉及经营范围登记时，应区分一般经营项目与依法须经批准的许可经营项目。"))
    if any(keyword in "\n".join([query, *snippets]) for keyword in ("当地", "窗口", "政务服务", "一网通办", "e窗通")):
        risks.append(RiskFlag(level="info", message="不同地区办理口径可能不同，应以当地政务平台或窗口公示为准。"))
    if not risks:
        risks.append(RiskFlag(level="info", message="建议正式答复前复核资料版本和当地公开口径。"))

    return EvidencePack(
        query=query,
        intent=intent,
        query_variants=query_variants or build_query_variants(query, tags),
        scenario_tags=tags,
        retrieval_strategy="GraphRAG local search + BM25 keyword supplement",
        ranking_strategy="RRF fusion + lexical cross-signal rerank",
        sources=normalized_sources,
        key_facts=key_facts,
        risk_flags=risks,
    )
