from __future__ import annotations

import sqlite3
from pathlib import Path

from reggraph_assistant.persistence import AppStateStore


def test_ping_returns_false_on_filesystem_error(tmp_path: Path) -> None:
    file_path = tmp_path / "not_a_directory"
    file_path.write_text("x", encoding="utf-8")
    backend = AppStateStore(file_path / "db.sqlite3")

    assert backend.ping() is False


def test_initialize_creates_parent_directory_and_table(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "state" / "app.sqlite3"
    backend = AppStateStore(db_path)

    backend.initialize()

    assert db_path.exists()
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'interaction_history'"
        ).fetchone()
    finally:
        conn.close()
    assert row == ("interaction_history",)
