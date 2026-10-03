from __future__ import annotations

from typing import Any, Iterable

from privacy.hashing import hash_identifier
from privacy.sanitizer import REDACTED, sanitize_literals

KNOWN_TABLES = {
    "customers": "table_001",
    "orders": "table_002",
    "products": "table_003",
    "transactions": "table_004",
    "order_items": "table_005",
}

KNOWN_COLUMNS = {
    "customer_id": "column_001",
    "name": "column_002",
    "email": "column_003",
    "phone": "column_004",
    "address": "column_005",
    "created_at": "column_006",
    "order_id": "column_007",
    "amount": "column_008",
    "status": "column_009",
    "product_id": "column_010",
    "sku": "column_011",
    "category": "column_012",
    "price": "column_013",
    "order_item_id": "column_014",
    "quantity": "column_015",
    "unit_price": "column_016",
    "transaction_id": "column_017",
    "method": "column_018",
    "order_count": "column_019",
    "total_amount": "column_020",
    "txn_count": "column_021",
    "total": "column_022",
}


class Anonymizer:
    def __init__(self) -> None:
        self.table_map: dict[str, str] = dict(KNOWN_TABLES)
        self.column_map: dict[str, str] = dict(KNOWN_COLUMNS)
        self.literals_removed = 0

    def hash_identifier(self, value: str, prefix: str = "X") -> str:
        return hash_identifier(value, prefix=prefix)

    def table_token(self, name: str) -> str:
        key = (name or "").lower()
        if key not in self.table_map:
            self.table_map[key] = self.hash_identifier(key, prefix="T")
        return self.table_map[key]

    def column_token(self, name: str) -> str:
        key = (name or "").lower()
        if key not in self.column_map:
            self.column_map[key] = self.hash_identifier(key, prefix="C")
        return self.column_map[key]

    def anonymize_query(self, sql: str) -> str:
        sanitized, count = sanitize_literals(sql)
        self.literals_removed += count
        result = sanitized
        for original, token in sorted(self.table_map.items(), key=lambda kv: len(kv[0]), reverse=True):
            result = _replace_ident(result, original, token)
        for original, token in sorted(self.column_map.items(), key=lambda kv: len(kv[0]), reverse=True):
            result = _replace_ident(result, original, token)
        return result

    def anonymize_schema(self, tables: Iterable[str], columns: Iterable[str]) -> dict[str, Any]:
        return {
            "tables": {name: self.table_token(name) for name in tables},
            "columns": {name: self.column_token(name) for name in columns},
        }

    def anonymize_plan(self, node: dict[str, Any]) -> dict[str, Any]:
        def walk(item: Any) -> Any:
            if isinstance(item, list):
                return [walk(child) for child in item]
            if not isinstance(item, dict):
                if isinstance(item, str):
                    return self._anonymize_text(item)
                return item
            out = {}
            for key, value in item.items():
                if key in {"relation", "alias"} and isinstance(value, str):
                    out[key] = self.table_token(value)
                elif key in {"index_name"} and isinstance(value, str):
                    out[key] = self.hash_identifier(value, prefix="I")
                elif key in {"filter", "join_filter", "hash_cond", "merge_cond", "index_cond"} and isinstance(value, str):
                    out[key] = self._anonymize_text(value)
                else:
                    out[key] = walk(value)
            return out

        return walk(node)

    def _anonymize_text(self, text: str) -> str:
        sanitized, count = sanitize_literals(text)
        self.literals_removed += count
        result = sanitized
        for original, token in self.table_map.items():
            result = _replace_ident(result, original, token)
        for original, token in self.column_map.items():
            result = _replace_ident(result, original, token)
        return result

    def stats(self) -> dict[str, int]:
        return {
            "raw_values_exposed_to_ai": 0,
            "sensitive_literals_removed": self.literals_removed,
            "anonymized_tables": len(self.table_map),
            "anonymized_columns": len(self.column_map),
        }


def anonymize_query(sql: str) -> str:
    return Anonymizer().anonymize_query(sql)


def anonymize_plan(node: dict[str, Any]) -> dict[str, Any]:
    return Anonymizer().anonymize_plan(node)


def anonymize_schema(tables: Iterable[str], columns: Iterable[str]) -> dict[str, Any]:
    return Anonymizer().anonymize_schema(tables, columns)


def _replace_ident(text: str, original: str, token: str) -> str:
    if not original:
        return text
    import re

    return re.sub(rf"\b{re.escape(original)}\b", token, text, flags=re.IGNORECASE)


def privacy_demo_pair() -> dict[str, str]:
    raw = "SELECT name FROM customers WHERE email = 'john@example.com';"
    return {"raw": raw, "anonymized": anonymize_query(raw)}
