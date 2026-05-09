from __future__ import annotations

from pathlib import Path

from reggraph_assistant.sqlite_state_backend import SqliteStateBackend


def test_ping_returns_false_on_filesystem_error(tmp_path: Path) -> None:
    file_path = tmp_path / 'not_a_directory'
    file_path.write_text('x', encoding='utf-8')
    backend = SqliteStateBackend(file_path / 'db.sqlite3')

    assert backend.ping() is False
