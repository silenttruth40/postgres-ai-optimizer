from privacy.anonymizer import Anonymizer, anonymize_query, hash_identifier
from privacy.sanitizer import REDACTED, sanitize_literals


def test_literals_are_removed():
    sql = "SELECT name FROM customers WHERE email = 'john@example.com' AND phone = '555-0100'"
    cleaned, count = sanitize_literals(sql)
    assert "john@example.com" not in cleaned
    assert "555-0100" not in cleaned
    assert REDACTED in cleaned
    assert count >= 2


def test_query_anonymization_is_structural():
    sql = "SELECT name FROM customers WHERE email = 'john@example.com'"
    out = anonymize_query(sql)
    assert "customers" not in out.lower()
    assert "john@example.com" not in out
    assert "table_001" in out
    assert REDACTED in out


def test_hashing_is_deterministic():
    assert hash_identifier("customers", prefix="T") == hash_identifier("customers", prefix="T")
    a = Anonymizer()
    b = Anonymizer()
    assert a.table_token("orders") == b.table_token("orders")
    assert a.column_token("customer_id") == b.column_token("customer_id")


def test_reverse_mapping_deanonymizes_query():
    anon = Anonymizer()
    sql = "SELECT name, email FROM customers WHERE email = 'john@example.com'"
    anonymized = anon.anonymize_query(sql)
    assert "table_001" in anonymized
    assert "column_002" in anonymized
    assert "customers" not in anonymized.lower()
    
    # Reconstruct back
    reconstructed = anon.deanonymize_query(anonymized)
    assert "customers" in reconstructed.lower()
    assert "name" in reconstructed.lower()
    assert "email" in reconstructed.lower()
    assert "table_001" not in reconstructed


def test_candidate_deanonymization():
    anon = Anonymizer()
    candidate = {
        "candidate_id": "C001",
        "type": "CREATE_COMPOSITE_INDEX",
        "table": "table_002",
        "columns": ["column_001", "column_006"],
        "sql": "CREATE INDEX idx_test ON table_002 (column_001, column_006)",
        "rewritten_sql": "SELECT column_001 FROM table_002",
        "reason": "Speed up lookup on table_002",
    }
    translated = anon.deanonymize_candidate(candidate)
    assert translated["table"] == "orders"
    assert translated["columns"] == ["customer_id", "created_at"]
    assert "orders" in translated["sql"]
    assert "orders" in translated["rewritten_sql"]
    assert "orders" in translated["reason"]

