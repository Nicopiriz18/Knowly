"""SQLite storage for users, access requests and one-time passwords."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from config import settings

_DB_FILE = Path(settings.data_dir) / "knowly.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    email TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected')),
    created_at REAL NOT NULL,
    decided_at REAL,
    token_version INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS otp_codes (
    email TEXT PRIMARY KEY,
    code_hash TEXT NOT NULL,
    expires_at REAL NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    sent_at REAL NOT NULL
);
"""


@contextmanager
def get_conn():
    """Yield a connection that commits on success and rolls back on error."""
    conn = sqlite3.connect(_DB_FILE, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    _DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(_SCHEMA)
