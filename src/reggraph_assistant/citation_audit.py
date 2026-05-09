from __future__ import annotations

import re
from typing import Literal

from .schemas import Citation, CitationAuditReport


CITATION_PATTERN = re.compile(r"\[(\d+)\]")


def normalize_citation_indices(sources: list[Citation]) -> list[Citation]:
    """规范化引用索引（幂等操作）

    Args:
        sources: 引用来源列表

    Returns:
        规范化后的引用列表
    """
    if not sources:
        return []

    # 检查是否已经规范化（所有 index 都已设置且从 1 开始连续）
    if all(s.index > 0 for s in sources):
        expected_indices = list(range(1, len(sources) + 1))
        actual_indices = [s.index for s in sources]
        if actual_indices == expected_indices:
            return sources  # 已规范化，直接返回

    # 需要规范化
    normalized: list[Citation] = []
    for index, source in enumerate(sources, start=1):
        normalized.append(
            Citation(
                index=index,
                source_id=source.source_id,
                document_name=source.document_name,
                snippet=source.snippet,
            )
        )
    return normalized


def bind_citation_markers(answer: str, sources: list[Citation], max_markers: int = 3) -> str:
    clean_answer = answer.strip()
    if not sources or CITATION_PATTERN.search(clean_answer):
        return clean_answer

    markers = " ".join(f"[{source.index if source.index is not None else index}]" for index, source in enumerate(sources[:max_markers], start=1))
    return f"{clean_answer}\n\n**来源片段**：{markers}"


def audit_citations(answer: str, sources: list[Citation], min_coverage: float = 0.8) -> CitationAuditReport:
    """审计引用覆盖率和有效性

    Args:
        answer: 答案文本
        sources: 来源列表
        min_coverage: 最小引用覆盖率阈值（默认 0.8，政务场景建议）
    """
    normalized_sources = normalize_citation_indices(sources)
    source_indices = {source.index for source in normalized_sources if source.index > 0}
    cited_indices = sorted({int(match) for match in CITATION_PATTERN.findall(answer)})
    valid_cited_indices = [index for index in cited_indices if index in source_indices]
    invalid_indices = [index for index in cited_indices if index not in source_indices]
    uncited_indices = sorted(source_indices - set(valid_cited_indices))

    warnings: list[str] = []
    has_sources = bool(normalized_sources)
    has_citations = bool(cited_indices)
    has_invalid = bool(invalid_indices)

    if not has_sources:
        warnings.append("回答没有返回来源片段。")
    elif not has_citations:
        warnings.append("回答正文没有来源编号。")

    if has_invalid:
        warnings.append("回答包含不存在的来源编号。")

    citation_coverage = len(valid_cited_indices) / len(normalized_sources) if has_sources else 0.0
    status: Literal["pass", "warn", "fail"]
    if not has_sources:
        status = "fail"
    elif citation_coverage >= min_coverage and not has_invalid:
        status = "pass"
    else:
        status = "warn"

    return CitationAuditReport(
        source_count=len(normalized_sources),
        cited_indices=valid_cited_indices,
        uncited_indices=uncited_indices,
        invalid_indices=invalid_indices,
        citation_coverage=round(citation_coverage, 4),
        status=status,
        warnings=warnings,
    )
