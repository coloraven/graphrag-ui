from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from reggraph_assistant.app import create_app
from reggraph_assistant.paths import resolve_paths
from reggraph_assistant.settings import EmbeddingConfig, LLMConfig, Settings


def make_settings(tmp_path: Path) -> Settings:
    root = tmp_path / "app"
    root.mkdir(parents=True, exist_ok=True)
    return Settings(
        paths=resolve_paths(root),
        llm=LLMConfig(
            api_key="key",
            model="llm-model",
            api_base="https://example.com/v1",
        ),
        embedding=EmbeddingConfig(
            api_key="embed",
            model="embedding-model",
            api_base="https://embed.example.com/v1",
        ),
    )


def test_workflow_request_uses_schema_limit(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path))
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/api/workflow/run", json={"task": "x" * 1001, "context": ""})

    assert response.status_code == 422


def test_document_upload_rejects_missing_filename(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path))
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/api/documents/upload",
        content=b"hello",
        headers={"Content-Type": "application/octet-stream"},
    )

    assert response.status_code == 422


def test_workflow_request_accepts_submitted_materials_and_returns_workflow_response(
    monkeypatch,
    tmp_path: Path,
) -> None:
    app = create_app(make_settings(tmp_path))
    client = TestClient(app, raise_server_exceptions=False)

    fake_run_workflow = AsyncMock(
        return_value={
            "intent": "checklist",
            "answer": "## 结论\n\n材料基本齐全。",
            "content_format": "markdown",
            "steps": [],
            "sources": [],
            "service_context": {
                "task_type": "material_check",
                "in_scope": True,
                "handoff_required": False,
                "slots": {},
                "missing_slots": [],
                "boundary_reason": "",
            },
            "evidence_pack": {
                "query": "",
                "intent": "",
                "query_variants": [],
                "scenario_tags": [],
                "retrieval_strategy": "",
                "ranking_strategy": "",
                "sources": [],
                "key_facts": [],
                "risk_flags": [],
            },
            "citation_audit": {
                "source_count": 0,
                "cited_indices": [],
                "uncited_indices": [],
                "invalid_indices": [],
                "citation_coverage": 0.0,
                "status": "pass",
                "warnings": [],
            },
        }
    )
    monkeypatch.setattr("reggraph_assistant.app.run_workflow", fake_run_workflow)

    response = client.post(
        "/api/workflow/run",
        json={
            "task": "公司设立登记前，现有材料是否足够进入提交阶段？",
            "submitted_materials": ["公司章程", "法定代表人身份证明"],
            "context": "",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "checklist"
    assert body["service_context"]["task_type"] == "material_check"
    assert "answer" in body
    assert "steps" in body
    assert "sources" in body
    fake_run_workflow.assert_awaited_once()


def test_workflow_request_rejects_overlong_material_item(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path))
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/api/workflow/run",
        json={
            "task": "公司设立登记前，现有材料是否足够进入提交阶段？",
            "submitted_materials": ["x" * 501],
            "context": "",
        },
    )

    assert response.status_code == 400
