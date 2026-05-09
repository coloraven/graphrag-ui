from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from reggraph_assistant.paths import resolve_paths
from reggraph_assistant.schemas import Citation, ServiceContext
from reggraph_assistant.settings import Settings
from reggraph_assistant.workflow import run_workflow


def make_settings(tmp_path: Path) -> Settings:
    root = tmp_path / 'workflow'
    root.mkdir(parents=True, exist_ok=True)
    return Settings(
        paths=resolve_paths(root),
        api_key='key',
        embedding_api_key='embed',
        llm_model='llm-model',
        embedding_model='embedding-model',
        api_base='https://example.com/v1',
        embedding_api_base='https://embed.example.com/v1',
    )


@pytest.mark.asyncio
async def test_cached_workflow_response_includes_consistent_evidence_and_audit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    cached_sources = [
        Citation(index=1, source_id='s1', document_name='Doc A', snippet='依据内容 A'),
        Citation(index=2, source_id='s2', document_name='Doc B', snippet='依据内容 B'),
    ]

    class FakeCache:
        def __init__(self, settings: Settings):
            self.settings = settings

        def get(self, query: str, intent: str) -> tuple[str, list[Citation]] | None:
            return ('结论如下\n\n**来源片段**：[1] [2]', cached_sources)

        def put(self, *args: Any, **kwargs: Any) -> None:
            raise AssertionError('cache.put should not be called on cache hit')

    class FakePlannerAgent:
        def __init__(self, settings: Settings):
            self.settings = settings

        def analyze_task(self, task: str, context: str) -> dict[str, Any]:
            return {
                'intent': 'policy_answer',
                'service_context': ServiceContext(),
                'scenario_tags': ['公司登记'],
                'query_variants': [task],
            }

    monkeypatch.setattr('reggraph_assistant.workflow.SemanticCache', FakeCache)
    monkeypatch.setattr('reggraph_assistant.agents.planner.PlannerAgent', FakePlannerAgent)

    response = await run_workflow('公司登记需要哪些材料？', settings)

    assert response.sources == cached_sources
    assert response.evidence_pack.sources == cached_sources
    assert response.citation_audit.source_count == 2
    assert response.citation_audit.cited_indices == [1, 2]
    assert response.citation_audit.citation_coverage == 1.0
    assert response.steps[0].key == 'cache'
