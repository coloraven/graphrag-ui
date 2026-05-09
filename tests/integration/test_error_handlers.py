from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from reggraph_assistant.error_handlers import register_error_handlers


def test_general_exception_handler_hides_raw_exception_text() -> None:
    app = FastAPI()
    register_error_handlers(app)

    @app.get('/boom')
    async def boom() -> None:
        raise RuntimeError('secret token leaked')

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get('/boom')

    assert response.status_code == 500
    payload = response.json()
    assert payload == {
        'error': 'Internal server error',
        'path': '/boom',
    }
    assert 'secret token leaked' not in response.text
