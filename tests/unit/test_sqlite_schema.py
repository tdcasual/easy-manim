from __future__ import annotations

import sqlite3

from video_agent.adapters.storage.sqlite_schema import ensure_column


def test_ensure_column_skips_missing_table() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row

    ensure_column(connection, "missing_table", "new_col", "TEXT")

    rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'missing_table'").fetchall()
    assert rows == []
