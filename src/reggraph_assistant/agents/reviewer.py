"""Reviewer Agent - 结果审查和质量控制"""
from __future__ import annotations

from typing import Any

from .base import BaseAgent
from .quality import QualityEvaluator
from .state_types import ReviewerState
from ..schemas import Citation, CitationAuditReport, EvidencePack
from ..settings import Settings


class ReviewerAgent(BaseAgent):
    """审查 Agent - 负责结果质量控制和审计"""

    def __init__(self, settings: Settings):
        super().__init__(settings)
        self.evaluator = QualityEvaluator(settings)

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """执行审查逻辑

        Args:
            state: 输入状态

        Returns:
            输出状态
        """
        return self.review(
            task=state["task"],
            intent=state["intent"],
            answer=state["answer"],
            sources=state["sources"],
            scenario_tags=state.get("scenario_tags", []),
            query_variants=state.get("query_variants", []),
        )

    def review(
        self,
        task: str,
        intent: str,
        answer: str,
        sources: list[Citation],
        scenario_tags: list[str],
        query_variants: list[str],
    ) -> ReviewerState:
        """审查生成结果

        职责：
        1. 构建 Evidence Pack（依据包）
        2. 审计引用覆盖率
        3. 检查答案质量
        4. 识别潜在风险
        """
        from ..evidence import build_evidence_pack
        from ..citation_audit import audit_citations, normalize_citation_indices

        # 1. 规范化来源
        normalized_sources = normalize_citation_indices(sources)

        # 2. 构建 Evidence Pack
        evidence_pack = build_evidence_pack(
            query=task,
            intent=intent,
            sources=normalized_sources,
            scenario_tags=scenario_tags,
            query_variants=query_variants,
        )

        # 3. 审计引用（使用配置的覆盖率阈值）
        citation_audit = audit_citations(answer, normalized_sources, min_coverage=self.settings.quality.min_citation_coverage)

        # 4. 使用统一的质量评估器
        metrics = self.evaluator.evaluate_answer(task, answer, normalized_sources, intent)

        # 5. 识别问题（传入 citation_audit 以获取更详细的引用信息）
        issues = self.evaluator.identify_issues(metrics, normalized_sources, citation_audit)

        # 6. 添加 Evidence Pack 相关的问题
        if len(evidence_pack.key_facts) == 0:
            issues.append("未提取到关键依据")

        critical_risks = [r for r in evidence_pack.risk_flags if r.level == "warning"]
        if critical_risks:
            issues.append(f"发现 {len(critical_risks)} 个警告级风险")

        return ReviewerState(
            answer=answer,
            sources=normalized_sources,
            evidence_pack=evidence_pack,
            citation_audit=citation_audit,
            quality_score=metrics.overall_score,
            issues=issues,
        )
