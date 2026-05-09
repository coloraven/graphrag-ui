from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from reggraph_assistant.paths import resolve_paths
from reggraph_assistant.schemas import Citation, CitationAuditReport, EvidencePack, ServiceContext
from reggraph_assistant.settings import Settings
from reggraph_assistant.workflow import run_workflow


def make_settings(tmp_path: Path) -> Settings:
    root = tmp_path / 'planner-opt'
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
async def test_workflow_cache_miss_reuses_initial_planner_result(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    planner_calls = {'count': 0}

    class FakeCache:
        def __init__(self, settings: Settings):
            self.settings = settings

        def get(self, query: str, intent: str) -> None:
            return None

        def put(self, *args: Any, **kwargs: Any) -> None:
            return None

    class FakePlannerAgent:
        def __init__(self, settings: Settings):
            self.settings = settings

        def analyze_task(self, task: str, context: str) -> dict[str, Any]:
            planner_calls['count'] += 1
            return {
                'intent': 'policy_answer',
                'service_context': ServiceContext(),
                'scenario_tags': ['公司登记'],
                'query_variants': [task],
                'retrieval_plan': {'use_graphrag': True},
            }

    monkeypatch.setattr('reggraph_assistant.workflow.SemanticCache', FakeCache)
    monkeypatch.setattr('reggraph_assistant.agents.planner.PlannerAgent', FakePlannerAgent)

    async def fake_ainvoke(self, initial_state: dict[str, Any]) -> dict[str, Any]:
        return {
            **initial_state,
            'answer': '结论\n\n**来源片段**：[1]',
            'sources': [Citation(index=1, source_id='s1', document_name='Doc A', snippet='依据 A')],
            'quality_score': 0.8,
            'evidence_pack': EvidencePack(sources=[Citation(index=1, source_id='s1', document_name='Doc A', snippet='依据 A')]),
            'citation_audit': CitationAuditReport(source_count=1, cited_indices=[1], citation_coverage=1.0, status='pass'),
            'steps': [],
        }

    monkeypatch.setattr('langgraph.pregel.main.Pregel.ainvoke', fake_ainvoke)

    response = await run_workflow('公司登记需要哪些材料？', settings)

    assert planner_calls['count'] == 1
    assert response.answer.startswith('结论')


@pytest.mark.asyncio
async def test_workflow_passes_submitted_materials_into_initial_state(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = make_settings(tmp_path)

    class FakeCache:
        def __init__(self, settings: Settings):
            self.settings = settings

        def get(self, query: str, intent: str) -> None:
            return None

        def put(self, *args: Any, **kwargs: Any) -> None:
            return None

    class FakePlannerAgent:
        def __init__(self, settings: Settings):
            self.settings = settings

        def analyze_task(self, task: str, context: str) -> dict[str, Any]:
            return {
                'intent': 'checklist',
                'service_context': ServiceContext(task_type='material_check'),
                'scenario_tags': ['公司登记'],
                'query_variants': [task],
                'retrieval_plan': {'use_graphrag': True},
            }

    captured: dict[str, Any] = {}

    async def fake_ainvoke(self, initial_state: dict[str, Any]) -> dict[str, Any]:
        captured.update(initial_state)
        return {
            **initial_state,
            'answer': '结论',
            'sources': [],
            'quality_score': 0.8,
            'evidence_pack': EvidencePack(),
            'citation_audit': CitationAuditReport(status='pass'),
            'steps': [],
        }

    monkeypatch.setattr('reggraph_assistant.workflow.SemanticCache', FakeCache)
    monkeypatch.setattr('reggraph_assistant.agents.planner.PlannerAgent', FakePlannerAgent)
    monkeypatch.setattr('langgraph.pregel.main.Pregel.ainvoke', fake_ainvoke)

    await run_workflow('公司登记需要哪些材料？', settings, submitted_materials=['公司章程', '住所使用证明'])

    assert captured['submitted_materials'] == ['公司章程', '住所使用证明']


@pytest.mark.asyncio
async def test_material_check_skips_semantic_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    cache_calls = {'get': 0, 'put': 0}

    class FakeCache:
        def __init__(self, settings: Settings):
            self.settings = settings

        def get(self, query: str, intent: str) -> None:
            cache_calls['get'] += 1
            return None

        def put(self, *args: Any, **kwargs: Any) -> None:
            cache_calls['put'] += 1

    class FakePlannerAgent:
        def __init__(self, settings: Settings):
            self.settings = settings

        def analyze_task(self, task: str, context: str) -> dict[str, Any]:
            return {
                'intent': 'checklist',
                'service_context': ServiceContext(task_type='material_check'),
                'scenario_tags': ['公司登记'],
                'query_variants': [task],
                'retrieval_plan': {'use_graphrag': True},
            }

    async def fake_ainvoke(self, initial_state: dict[str, Any]) -> dict[str, Any]:
        return {
            **initial_state,
            'answer': '结论',
            'sources': [],
            'quality_score': 0.9,
            'evidence_pack': EvidencePack(),
            'citation_audit': CitationAuditReport(status='pass'),
            'steps': [],
        }

    monkeypatch.setattr('reggraph_assistant.workflow.SemanticCache', FakeCache)
    monkeypatch.setattr('reggraph_assistant.agents.planner.PlannerAgent', FakePlannerAgent)
    monkeypatch.setattr('langgraph.pregel.main.Pregel.ainvoke', fake_ainvoke)

    await run_workflow('公司登记需要哪些材料？', settings, submitted_materials=['公司章程'])

    assert cache_calls == {'get': 0, 'put': 0}


@pytest.mark.asyncio
async def test_planner_node_uses_precomputed_plan(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from reggraph_assistant.workflow_nodes import planner_node

    settings = make_settings(tmp_path)
    planner_calls = {'count': 0}

    class FakePlannerAgent:
        def __init__(self, settings: Settings):
            self.settings = settings

        def analyze_task(self, task: str, context: str) -> dict[str, Any]:
            planner_calls['count'] += 1
            return {}

    monkeypatch.setattr('reggraph_assistant.workflow_nodes.PlannerAgent', FakePlannerAgent)

    state = {
        'task': 't',
        'context': '',
        'service_context': ServiceContext(),
        'intent': 'policy_answer',
        'scenario_tags': ['公司登记'],
        'query_variants': ['t'],
        'retrieval_plan': {'use_graphrag': True},
        'steps': [],
    }

    result = planner_node(state, settings)

    assert planner_calls['count'] == 0
    assert result['intent'] == 'policy_answer'
    assert result['steps'][0].detail.startswith('复用预规划结果')
