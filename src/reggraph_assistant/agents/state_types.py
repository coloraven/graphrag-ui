"""Agent 状态类型定义

统一管理所有 Agent 的状态类型定义
"""
from __future__ import annotations

from typing import Any, TypedDict

from ..schemas import Citation, CitationAuditReport, EvidencePack, ServiceContext


class PlannerState(TypedDict, total=False):
    """Planner Agent 状态"""
    task: str
    context: str
    service_context: ServiceContext
    intent: str
    scenario_tags: list[str]
    query_variants: list[str]
    retrieval_plan: dict[str, Any]


class RetrieverState(TypedDict, total=False):
    """Retriever Agent 状态"""
    query: str
    query_variants: list[str]
    graphrag_sources: list[Citation]
    bm25_sources: list[Citation]
    vector_sources: list[Citation]
    fused_sources: list[Citation]


class GeneratorState(TypedDict, total=False):
    """Generator Agent 状态"""
    task: str
    context: str
    intent: str
    sources: list[Citation]
    answer: str


class ReviewerState(TypedDict, total=False):
    """Reviewer Agent 状态"""
    answer: str
    sources: list[Citation]
    evidence_pack: EvidencePack
    citation_audit: CitationAuditReport
    quality_score: float
    issues: list[str]
