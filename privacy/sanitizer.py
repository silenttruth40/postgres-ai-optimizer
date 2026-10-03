from __future__ import annotations

import re

import sqlparse
from sqlparse.sql import Token
from sqlparse.tokens import Literal, String, Number

REDACTED = "<REDACTED>"

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\+?\d[\d\-\s()]{7,}\d")


def sanitize_literals(sql: str) -> tuple[str, int]:
    """Replace SQL literals and obvious PII patterns. Returns (sql, count)."""
    if not sql:
        return sql, 0
    parsed = sqlparse.parse(sql)
    if not parsed:
        return sql, 0
    count = 0
    parts: list[str] = []

    def walk(token: Token) -> None:
        nonlocal count
        if token.is_group:
            for child in token.tokens:
                walk(child)
            return
        if token.ttype in String or token.ttype in Literal.String:
            parts.append(REDACTED)
            count += 1
            return
        if token.ttype in Number or token.ttype in Literal.Number:
            parts.append(REDACTED)
            count += 1
            return
        value = str(token.value)
        if EMAIL_RE.search(value) or PHONE_RE.search(value):
            parts.append(EMAIL_RE.sub(REDACTED, PHONE_RE.sub(REDACTED, value)))
            count += 1
            return
        parts.append(value)

    for stmt in parsed:
        for token in stmt.tokens:
            walk(token)
    text = "".join(parts)
    text, extra = _redact_patterns(text)
    return text, count + extra


def _redact_patterns(text: str) -> tuple[str, int]:
    extra = 0
    for pattern in (EMAIL_RE, PHONE_RE):
        matches = pattern.findall(text)
        extra += len(matches)
        text = pattern.sub(REDACTED, text)
    return text, extra
