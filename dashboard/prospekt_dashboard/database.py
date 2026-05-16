"""SQLite helpers for the PROSPEKT dashboard."""

from __future__ import annotations

import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_ROOT / "dashboard" / "prospekt.db"


def get_connection(database_path: Path = DATABASE_PATH) -> sqlite3.Connection:
    """Return a SQLite connection with row dictionaries enabled."""
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def count_zones(database_path: Path = DATABASE_PATH) -> int:
    """Return the number of zones stored in the dashboard database."""
    with get_connection(database_path) as connection:
        row = connection.execute("SELECT COUNT(*) AS total FROM zones").fetchone()
    return int(row["total"])
