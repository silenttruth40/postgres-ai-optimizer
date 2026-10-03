from __future__ import annotations

from sandbox.manager import apply_candidate, list_indexes, revert, validate_candidate


def execute_candidate(conn, candidate: dict) -> str | None:
    return apply_candidate(conn, candidate)


__all__ = ["apply_candidate", "execute_candidate", "list_indexes", "revert", "validate_candidate"]
