from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from pathlib import Path

from .citation_audit import audit_citations, normalize_citation_indices
from .schemas import EvalCase, EvalCaseResult, EvalReport, WorkflowResponse
from .settings import Settings


DEFAULT_EVAL_CASES_PATH = Path("eval") / "eval_cases.jsonl"


def load_eval_cases(path: Path) -> list[EvalCase]:
    if not path.exists():
        return []

    cases: list[EvalCase] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        cases.append(EvalCase.model_validate(json.loads(stripped)))
    return cases


def _contains_expected_document(retrieved_documents: list[str], expected_documents: list[str]) -> bool:
    if not expected_documents:
        return bool(retrieved_documents)
    normalized_retrieved = [document.lower() for document in retrieved_documents]
    return any(
        expected.lower() in document
        for expected in expected_documents
        for document in normalized_retrieved
    )


def _keyword_coverage(answer: str, expected_keywords: list[str]) -> float:
    if not expected_keywords:
        return 1.0
    lowered_answer = answer.lower()
    hits = sum(1 for keyword in expected_keywords if keyword.lower() in lowered_answer)
    return hits / len(expected_keywords)


def _source_keyword_coverage(snippets: list[str], expected_keywords: list[str]) -> float:
    if not expected_keywords:
        return 1.0
    joined_snippets = "\n".join(snippets).lower()
    hits = sum(1 for keyword in expected_keywords if keyword.lower() in joined_snippets)
    return hits / len(expected_keywords)


async def evaluate_case(
    eval_case: EvalCase,
    settings: Settings,
    workflow_runner: Callable[[str, Settings, str, list[str] | None], Awaitable[WorkflowResponse]],
) -> EvalCaseResult:
    response = await workflow_runner(eval_case.question, settings, "", None)
    sources = normalize_citation_indices(response.sources)
    audit = audit_citations(response.answer, sources)
    retrieved_documents = sorted({source.document_name for source in sources})
    retrieval_hit = _contains_expected_document(retrieved_documents, eval_case.expected_documents)
    keyword_coverage = _keyword_coverage(response.answer, eval_case.expected_keywords)
    source_keyword_coverage = _source_keyword_coverage([source.snippet for source in sources], eval_case.expected_keywords)
    citation_coverage = audit.citation_coverage
    warnings = list(audit.warnings)

    passed = retrieval_hit and keyword_coverage >= 0.5 and citation_coverage > 0
    if not retrieval_hit:
        warnings.append("未命中期望来源文档。")
    if keyword_coverage < 0.5:
        warnings.append("答案关键词覆盖不足。")
    if source_keyword_coverage < 0.5:
        warnings.append("来源片段关键词覆盖不足。")
    if citation_coverage == 0:
        warnings.append("答案缺少有效来源编号覆盖。")

    return EvalCaseResult(
        question=eval_case.question,
        passed=passed,
        expected_documents=eval_case.expected_documents,
        retrieved_documents=retrieved_documents,
        retrieval_hit=retrieval_hit,
        keyword_coverage=round(keyword_coverage, 4),
        source_keyword_coverage=round(source_keyword_coverage, 4),
        citation_coverage=round(citation_coverage, 4),
        answer_preview=response.answer[:240],
        warnings=warnings,
    )


def build_eval_report(results: list[EvalCaseResult]) -> EvalReport:
    total = len(results)
    passed = sum(1 for result in results if result.passed)
    retrieval_hits = sum(1 for result in results if result.retrieval_hit)
    keyword_coverage_sum = sum(result.keyword_coverage for result in results)
    source_keyword_coverage_sum = sum(result.source_keyword_coverage for result in results)
    citation_coverage_sum = sum(result.citation_coverage for result in results)

    return EvalReport(
        total_cases=total,
        passed_cases=passed,
        failed_cases=total - passed,
        retrieval_hit_rate=round(retrieval_hits / total, 4) if total else 0.0,
        keyword_coverage_rate=round(keyword_coverage_sum / total, 4) if total else 0.0,
        source_keyword_coverage_rate=round(source_keyword_coverage_sum / total, 4) if total else 0.0,
        citation_coverage_rate=round(citation_coverage_sum / total, 4) if total else 0.0,
        results=results,
    )


async def run_evaluation(
    settings: Settings,
    workflow_runner: Callable[[str, Settings, str, list[str] | None], Awaitable[WorkflowResponse]],
    cases_path: Path | None = None,
) -> EvalReport:
    path = cases_path or settings.paths.root / DEFAULT_EVAL_CASES_PATH
    cases = load_eval_cases(path)
    results = [await evaluate_case(eval_case, settings, workflow_runner=workflow_runner) for eval_case in cases]
    return build_eval_report(results)
