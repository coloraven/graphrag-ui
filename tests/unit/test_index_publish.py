from __future__ import annotations

from pathlib import Path

import pytest

from reggraph_assistant import indexing
from reggraph_assistant.indexing import STATUS_FILE, rebuild_index
from reggraph_assistant.paths import resolve_paths
from reggraph_assistant.settings import EmbeddingConfig, LLMConfig, Settings


def make_settings(tmp_path: Path) -> Settings:
    root = tmp_path / 'publish'
    root.mkdir(parents=True, exist_ok=True)
    return Settings(
        paths=resolve_paths(root),
        llm=LLMConfig(
            api_key='key',
            model='llm-model',
            api_base='https://example.com/v1',
        ),
        embedding=EmbeddingConfig(
            api_key='embed',
            model='embedding-model',
            api_base='https://embed.example.com/v1',
        ),
    )


def test_indexing_compat_exports() -> None:
    assert callable(indexing.read_document_preview)
    assert callable(indexing.save_uploaded_document_stream)
    assert callable(indexing.rebuild_index)
    assert indexing.STATUS_FILE == "status.yaml"


def test_atomic_publish_keeps_previous_index_until_swap(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    paths = settings.paths
    paths.workspace_dir.mkdir(parents=True, exist_ok=True)
    paths.index_dir.mkdir(parents=True, exist_ok=True)
    (paths.index_dir / 'old.txt').write_text('old', encoding='utf-8')

    output_dir = paths.graphrag_project_dir / 'output'
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / 'new.txt').write_text('new', encoding='utf-8')

    monkeypatch.setattr('reggraph_assistant.index_builder.ensure_graphrag_project', lambda *args, **kwargs: None)
    monkeypatch.setattr('reggraph_assistant.index_builder.normalize_documents', lambda *args, **kwargs: [Path('doc1.md')])
    monkeypatch.setattr('reggraph_assistant.index_builder.sync_normalized_to_graphrag_input', lambda *args, **kwargs: None)
    monkeypatch.setattr('reggraph_assistant.index_builder.run_graphrag_index', lambda *args, **kwargs: None)

    response = rebuild_index(settings)

    assert response.success is True
    assert not (paths.workspace_dir / 'index_previous').exists()
    assert not (paths.workspace_dir / 'index_next').exists()
    assert not (paths.index_dir / 'old.txt').exists()
    assert (paths.index_dir / 'new.txt').read_text(encoding='utf-8') == 'new'
    assert (paths.index_dir / STATUS_FILE).exists()
