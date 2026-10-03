from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg.rows import dict_row

from backend.config import Settings, get_settings


def connect(settings: Settings | None = None, sandbox: bool = False) -> psycopg.Connection:
    settings = settings or get_settings()
    return psycopg.connect(settings.dsn(sandbox=sandbox), row_factory=dict_row, autocommit=True)


@contextmanager
def get_connection(sandbox: bool = False) -> Iterator[psycopg.Connection]:
    conn = connect(sandbox=sandbox)
    try:
        yield conn
    finally:
        conn.close()


def ping(sandbox: bool = False) -> bool:
    try:
        with get_connection(sandbox=sandbox) as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False
