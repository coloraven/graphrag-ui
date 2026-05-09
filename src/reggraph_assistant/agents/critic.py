"""Critic Agent - 质量评估和改进建议"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .base import BaseAgent
from .quality import QualityEvaluator
from ..schemas import Citation
from ..settings import Settings


@dataclass
class Critique:
    """评估结果"""
    score: float  # 总体质量分数（0-1）
    is_acceptable: bool  # 是否达标
    issues: list[str]  # 发现的问题
    improvement_suggestions: list[str]  # 改进建议
    dimension_scores: dict[str, float]  # 各维度分数


class CriticAgent(BaseAgent):
    """Critic Agent - 质量评估和改进建议生成

    用于 Reflection Loop 中的质量评估
    """

    def __init__(self, settings: Settings):
        super().__init__(settings)
        self.evaluator = QualityEvaluator(settings)

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """执行评估逻辑

        Args:
            state: 输入状态

        Returns:
            输出状态
        """
        critique = self.evaluate(
            task=state["task"],
            answer=state["answer"],
            sources=state["sources"],
            intent=state["intent"],
        )
        return {
            "quality_score": critique.score,
            "is_acceptable": critique.is_acceptable,
            "issues": critique.issues,
            "improvement_suggestions": critique.improvement_suggestions,
        }

    def evaluate(
        self,
        task: str,
        answer: str,
        sources: list[Citation],
        intent: str = "policy_answer"
    ) -> Critique:
        """评估答案质量

        Args:
            task: 用户任务
            answer: 生成的答案
            sources: 引用来源
            intent: 任务意图

        Returns:
            Critique: 评估结果
        """
        # 使用统一的质量评估器
        metrics = self.evaluator.evaluate_answer(task, answer, sources, intent)

        # 判断是否达标
        is_acceptable = metrics.overall_score >= self.evaluator.quality_threshold

        # 识别问题
        issues = self.evaluator.identify_issues(metrics, sources)

        # 生成改进建议
        improvement_suggestions = self.evaluator.generate_suggestions(metrics, sources)

        return Critique(
            score=metrics.overall_score,
            is_acceptable=is_acceptable,
            issues=issues,
            improvement_suggestions=improvement_suggestions,
            dimension_scores={
                'relevance': metrics.relevance,
                'completeness': metrics.completeness,
                'accuracy': metrics.accuracy,
                'citation': metrics.citation,
                'expression': metrics.expression,
            }
        )
