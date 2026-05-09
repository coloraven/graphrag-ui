from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from reggraph_assistant.app import create_app
from reggraph_assistant.paths import resolve_paths
from reggraph_assistant.settings import EmbeddingConfig, LLMConfig, Settings


def make_settings(tmp_path: Path) -> Settings:
    root = tmp_path / 'upload'
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


def test_upload_existing_document_returns_409_without_overwrite(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    target = settings.paths.input_dir / 'sample.md'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('original', encoding='utf-8')

    app = create_app(settings)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        '/api/documents/upload?filename=sample.md',
        content=b'new content',
        headers={'Content-Type': 'application/octet-stream'},
    )

    assert response.status_code == 409
    assert target.read_text(encoding='utf-8') == 'original'


def test_streamed_upload_writes_chunks_in_order(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    target = settings.paths.input_dir / 'streamed.md'

    app = create_app(settings)
    client = TestClient(app, raise_server_exceptions=False)

    chunks = [b'part one\n', b'part two\n', b'part three']
    response = client.post(
        '/api/documents/upload?filename=streamed.md',
        content=iter(chunks),
        headers={'Content-Type': 'application/octet-stream'},
    )

    assert response.status_code == 200
    assert target.read_bytes() == b''.join(chunks)


def test_empty_upload_does_not_leave_partial_file(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    target = settings.paths.input_dir / 'empty.md'

    app = create_app(settings)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        '/api/documents/upload?filename=empty.md',
        content=iter([b'', b'']),
        headers={'Content-Type': 'application/octet-stream'},
    )

    assert response.status_code == 400
    assert not target.exists()
    assert not list(target.parent.glob(f'.{target.name}.*.uploading'))
