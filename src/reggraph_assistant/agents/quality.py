"""质量评估模块 - 合并 Critic 和 Reviewer 的共同逻辑"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..schemas import Citation, CitationAuditReport, EvidencePack
from ..settings import Settings

# 质量评估阈值常量
DEFAULT_QUALITY_THRESHOLD = 0.8
RELEVANCE_THRESHOLD = 0.7
COMPLETENESS_THRESHOLD = 0.7
ACCURACY_THRESHOLD = 0.8
CITATION_THRESHOLD = 0.6
EXPRESSION_THRESHOLD = 0.7
MIN_CITATION_COVERAGE_THRESHOLD = 0.5

# 中文停用词
CHINESE_STOPWORDS = frozenset({
    '的', '了', '是', '在', '有', '和', '与', '等', '吗', '呢', '？', '。',
    '啊', '呀', '吧', '嘛', '哦', '哈', '嗯', '唉', '这', '那', '个', '些',
    '为', '以', '及', '或', '但', '而', '且', '因', '所', '由', '从', '到',
})


@dataclass
class QualityMetrics:
    """质量指标"""
    relevance: float  # 相关性
    completeness: float  # 完整性
    accuracy: float  # 准确性
    citation: float  # 引用质量
    expression: float  # 表达质量
    coverage: float  # 来源覆盖率

    @property
    def overall_score(self) -> float:
        """计算总体分数（使用默认权重）"""
        return (
            self.relevance * 0.25 +
            self.completeness * 0.20 +
            self.accuracy * 0.25 +
            self.citation * 0.15 +
            self.expression * 0.15
        )


class QualityEvaluator:
    """质量评估器 - 统一的质量评估逻辑

    合并了 CriticAgent 和 ReviewerAgent 的评估功能
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.quality_threshold = DEFAULT_QUALITY_THRESHOLD

    def evaluate_answer(
        self,
        task: str,
        answer: str,
        sources: list[Citation],
        intent: str = "policy_answer"
    ) -> QualityMetrics:
        """评估答案质量

        Args:
            task: 用户任务
            answer: 生成的答案
            sources: 引用来源
            intent: 任务意图

        Returns:
            QualityMetrics: 质量指标
        """
        return QualityMetrics(
            relevance=self._evaluate_relevance(task, answer),
            completeness=self._evaluate_completeness(task, answer, intent),
            accuracy=self._evaluate_accuracy(answer, sources),
            citation=self._evaluate_citations(answer, sources),
            expression=self._evaluate_expression(answer),
            coverage=self._calculate_coverage(answer, sources),
        )

    def _evaluate_relevance(self, task: str, answer: str) -> float:
        """评估答案相关性"""
        task_keywords = set(task.lower().split()) - CHINESE_STOPWORDS
        answer_keywords = set(answer.lower().split()) - CHINESE_STOPWORDS

        if not task_keywords:
            return 0.5

        overlap = len(task_keywords & answer_keywords)
        coverage = overlap / len(task_keywords)

        if len(answer) < 50:
            coverage *= 0.7

        return min(coverage * 1.2, 1.0)

    def _evaluate_completeness(self, task: str, answer: str, intent: str) -> float:
        """评估答案完整性"""
        score = 0.7

        if intent == "checklist":
            if any(marker in answer for marker in ["1.", "•", "-"]):
                score += 0.2
            if any(keyword in answer for keyword in ["材料", "证件", "文件"]):
                score += 0.1
        elif intent == "policy_answer":
            if any(keyword in answer for keyword in ["依据", "规定", "法律"]):
                score += 0.15
            if len(answer) > 100:
                score += 0.15

        return min(score, 1.0)

    def _evaluate_accuracy(self, answer: str, sources: list[Citation]) -> float:
        """评估答案准确性"""
        score = 0.8

        if not sources:
            score -= 0.3
        elif len(sources) < 2:
            score -= 0.1

        citation_markers = [f"[{i}]" for i in range(1, 20)]
        has_citations = any(marker in answer for marker in citation_markers)
        if not has_citations and sources:
            score -= 0.2

        return max(score, 0.0)

    def _evaluate_citations(self, answer: str, sources: list[Citation]) -> float:
        """评估引用质量"""
        if not sources:
            return 0.3

        score = 0.5

        if len(sources) >= 3:
            score += 0.2
        elif len(sources) >= 2:
            score += 0.1

        citation_count = sum(1 for i in range(1, len(sources) + 1) if f"[{i}]" in answer)
        if citation_count >= len(sources) * 0.8:
            score += 0.2
        elif citation_count >= len(sources) * 0.5:
            score += 0.1

        unique_docs = len(set(s.document_name for s in sources))
        if unique_docs >= 2:
            score += 0.1

        return min(score, 1.0)

    def _evaluate_expression(self, answer: str) -> float:
        """评估表达质量"""
        score = 0.7

        length = len(answer)
        if 100 <= length <= 800:
            score += 0.1
        elif length < 50 or length > 1500:
            score -= 0.2

        if "\n\n" in answer or "\n" in answer:
            score += 0.1

        if "。。" in answer or "，，" in answer:
            score -= 0.1

        return min(max(score, 0.0), 1.0)

    def _calculate_coverage(self, answer: str, sources: list[Citation]) -> float:
        """计算来源覆盖率"""
        if not sources:
            return 0.0

        cited_count = sum(1 for i in range(1, len(sources) + 1) if f"[{i}]" in answer)
        return cited_count / len(sources)

    def identify_issues(
        self,
        metrics: QualityMetrics,
        sources: list[Citation],
        citation_audit: CitationAuditReport | None = None,
    ) -> list[str]:
        """识别质量问题

        Args:
            metrics: 质量指标
            sources: 引用来源
            citation_audit: 引用审计报告（可选）

        Returns:
            问题列表
        """
        issues = []

        if metrics.relevance < RELEVANCE_THRESHOLD:
            issues.append("答案相关性不足，未充分回答用户问题")

        if metrics.completeness < COMPLETENESS_THRESHOLD:
            issues.append("答案完整性不足，缺少关键信息")

        if metrics.accuracy < ACCURACY_THRESHOLD:
            issues.append("答案准确性存疑，缺乏可靠来源支持")

        if metrics.citation < CITATION_THRESHOLD:
            issues.append("引用质量不足，来源标注不清晰")

        if metrics.expression < EXPRESSION_THRESHOLD:
            issues.append("表达质量有待提升，结构或语言不够清晰")

        if metrics.coverage < MIN_CITATION_COVERAGE_THRESHOLD:
            issues.append(f"引用覆盖率低：{metrics.coverage:.1%}")

        if not sources:
            issues.append("未找到任何依据来源")

        return issues

    def generate_suggestions(self, metrics: QualityMetrics, sources: list[Citation]) -> list[str]:
        """生成改进建议

        Args:
            metrics: 质量指标
            sources: 引用来源

        Returns:
            改进建议列表
        """
        suggestions = []

        if metrics.relevance < RELEVANCE_THRESHOLD:
            suggestions.append("重新审视用户问题，确保答案直接回答问题的核心")

        if metrics.completeness < COMPLETENESS_THRESHOLD:
            suggestions.append("补充缺失的关键信息，覆盖问题的所有方面")

        if metrics.accuracy < ACCURACY_THRESHOLD:
            suggestions.append("检查答案中的事实陈述，确保有可靠来源支持")

        if metrics.citation < CITATION_THRESHOLD:
            suggestions.append("增加引用标记，明确指出每个关键信息的来源")

        if metrics.expression < EXPRESSION_THRESHOLD:
            suggestions.append("改进表达方式，使用更清晰的结构和语言")

        if len(sources) < 2:
            suggestions.append("当前来源不足，建议补充检索以获取更多支持材料")

        return suggestions
