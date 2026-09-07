"""Unit tests for the pure cleaning functions in etl.transform.transformations."""
from etl.transform.transformations import (
    clean_string,
    clean_email,
    clean_numeric,
    transform_customer_record,
    transform_order_record,
)


def test_clean_string_trims_whitespace():
    assert clean_string("  hello  ") == "hello"


def test_clean_string_empty_becomes_none():
    assert clean_string("") is None
    assert clean_string("   ") is None
    assert clean_string(None) is None


def test_clean_email_lowercases():
    assert clean_email("  John.Doe@EXAMPLE.com  ") == "john.doe@example.com"


def test_clean_email_empty_becomes_none():
    assert clean_email("") is None


def test_clean_numeric_parses_valid_number():
    assert clean_numeric("19.99") == 19.99


def test_clean_numeric_invalid_becomes_none():
    assert clean_numeric("not-a-number") is None
    assert clean_numeric("") is None


def test_transform_customer_record_maps_fields():
    raw = {
        "customer_id": "CUST0001",
        "first_name": " Jane ",
        "last_name": "Doe",
        "email": "JANE@EXAMPLE.COM",
        "phone": "555-1234",
        "address_line1": "123 Main St",
        "city": "Springfield",
        "state": "IL",
        "postal_code": "62704",
        "country": "USA",
        "created_at": "2024-01-01 00:00:00",
        "updated_at": "2024-01-01 00:00:00",
    }
    result = transform_customer_record(raw)
    assert result["customer_id"] == "CUST0001"
    assert result["first_name"] == "Jane"
    assert result["email"] == "jane@example.com"


def test_transform_order_record_defaults_currency():
    raw = {
        "order_id": "ORD00001",
        "customer_id": "CUST0001",
        "order_date": "2024-01-01",
        "status": "completed",
        "subtotal": "100.00",
        "tax": "7.00",
        "total_amount": "107.00",
        "currency": "",
        "created_at": "2024-01-01 00:00:00",
        "updated_at": "2024-01-01 00:00:00",
    }
    result = transform_order_record(raw)
    assert result["currency"] == "USD"
    assert result["total_amount"] == 107.00


def test_transform_order_record_missing_total_is_none():
    raw = {"order_id": "ORD00002", "customer_id": "CUST0001", "total_amount": ""}
    result = transform_order_record(raw)
    assert result["total_amount"] is None
