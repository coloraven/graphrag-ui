from __future__ import annotations

import os
from pathlib import Path
import threading
import time
from typing import Any

import pytest

from reggraph_assistant.indexing import IndexBuildError, run_graphrag_index
from reggraph_assistant.paths import resolve_paths
from reggraph_assistant.settings import EmbeddingConfig, LLMConfig, Settings


def make_settings(tmp_path: Path, api_key: str, embedding_key: str | None = None) -> Settings:
    root = tmp_path / api_key
    root.mkdir(parents=True, exist_ok=True)
    return Settings(
        paths=resolve_paths(root),
        llm=LLMConfig(
            api_key=api_key,
            model='llm-model',
            api_base='https://example.com/v1',
        ),
        embedding=EmbeddingConfig(
            api_key=embedding_key or f'{api_key}-embedding',
            model='embedding-model',
            api_base='https://embed.example.com/v1',
        ),
    )


def test_run_graphrag_index_restores_env_after_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = make_settings(tmp_path, 'test-key')
    monkeypatch.setenv('GRAPHRAG_API_KEY', 'original-key')
    monkeypatch.delenv('GRAPHRAG_API_KEY_EMBEDDING', raising=False)
    monkeypatch.setenv('GRAPHRAG_API_BASE', 'https://original.example.com/v1')
    monkeypatch.delenv('GRAPHRAG_API_BASE_EMBEDDING', raising=False)

    def fail_load_config(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError('load failure with secret details')

    monkeypatch.setattr('reggraph_assistant.index_builder.load_config', fail_load_config)

    with pytest.raises(IndexBuildError):
        run_graphrag_index(settings)

    assert os.environ['GRAPHRAG_API_KEY'] == 'original-key'
    assert os.environ['GRAPHRAG_API_BASE'] == 'https://original.example.com/v1'
    assert 'GRAPHRAG_API_KEY_EMBEDDING' not in os.environ
    assert 'GRAPHRAG_API_BASE_EMBEDDING' not in os.environ


def test_run_graphrag_index_isolates_env_between_concurrent_calls(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings_a = make_settings(tmp_path, 'key-a', 'embed-a')
    settings_b = make_settings(tmp_path, 'key-b', 'embed-b')

    monkeypatch.setenv('GRAPHRAG_API_KEY', 'original-key')
    monkeypatch.setenv('GRAPHRAG_API_KEY_EMBEDDING', 'original-embed')
    monkeypatch.setenv('GRAPHRAG_API_BASE', 'https://original.example.com/v1')
    monkeypatch.setenv('GRAPHRAG_API_BASE_EMBEDDING', 'https://original-embed.example.com/v1')

    observed_values: list[tuple[str, str, str, str]] = []
    observed_lock = threading.Lock()

    class DummyVectorStore:
        vector_size = 128

    class DummyConfig:
        vector_store = DummyVectorStore()

    def fake_load_config(*args: Any, **kwargs: Any) -> DummyConfig:
        return DummyConfig()

    def fake_validate_config_names(config: Any) -> None:
        return None

    async def fake_build_index(**kwargs: Any) -> list[Any]:
        current = (
            os.environ['GRAPHRAG_API_KEY'],
            os.environ['GRAPHRAG_API_KEY_EMBEDDING'],
            os.environ['GRAPHRAG_API_BASE'],
            os.environ['GRAPHRAG_API_BASE_EMBEDDING'],
        )
        with observed_lock:
            observed_values.append(current)
        time.sleep(0.05)
        return []

    monkeypatch.setattr('reggraph_assistant.index_builder.load_config', fake_load_config)
    monkeypatch.setattr('reggraph_assistant.index_builder.validate_config_names', fake_validate_config_names)
    monkeypatch.setattr('reggraph_assistant.index_builder.persist_vector_size', lambda *args, **kwargs: None)
    monkeypatch.setattr('reggraph_assistant.index_builder.build_index', fake_build_index)

    errors: list[BaseException] = []

    def runner(settings: Settings) -> None:
        try:
            run_graphrag_index(settings)
        except BaseException as exc:  # pragma: no cover
            errors.append(exc)

    thread_a = threading.Thread(target=runner, args=(settings_a,))
    thread_b = threading.Thread(target=runner, args=(settings_b,))
    thread_a.start()
    thread_b.start()
    thread_a.join(timeout=5)
    thread_b.join(timeout=5)

    assert not errors
    assert len(observed_values) == 2
    assert set(observed_values) == {
        ('key-a', 'embed-a', 'https://example.com/v1', 'https://embed.example.com/v1'),
        ('key-b', 'embed-b', 'https://example.com/v1', 'https://embed.example.com/v1'),
    }
    assert os.environ['GRAPHRAG_API_KEY'] == 'original-key'
    assert os.environ['GRAPHRAG_API_KEY_EMBEDDING'] == 'original-embed'
    assert os.environ['GRAPHRAG_API_BASE'] == 'https://original.example.com/v1'
    assert os.environ['GRAPHRAG_API_BASE_EMBEDDING'] == 'https://original-embed.example.com/v1'
