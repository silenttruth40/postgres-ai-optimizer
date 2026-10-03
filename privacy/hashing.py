from __future__ import annotations

import hashlib
import re

IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def hash_identifier(value: str, prefix: str = "X", length: int = 4) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:length].upper()
    return f"{prefix}_{digest}"


def is_safe_identifier(value: str) -> bool:
    return bool(IDENTIFIER_RE.match(value or ""))
