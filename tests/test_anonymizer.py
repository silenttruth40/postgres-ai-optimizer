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
