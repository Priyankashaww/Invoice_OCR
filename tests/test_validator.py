from decimal import Decimal

from src.validator import validate_invoice


def test_valid_invoice():
    # Canonical field names are used in production.
    invoice = {
        "invoice": "INV-101",
        "vendor": "ABC Technologies",
        "date": "2026-11-10",
        "currency": "INR",
        "subtotal": Decimal("1000.00"),
        "tax": Decimal("180.00"),
        "total": Decimal("1180.00"),
    }

    is_valid, errors = validate_invoice(invoice)

    assert is_valid is True
    assert errors == []


def test_legacy_invoice_and_date_aliases_are_supported():
    # Backward compatibility with the user's original test dictionary.
    invoice = {
        "invoice": "INV-101",
        "vendor": "ABC Technologies",
        "date": "2026-11-10",
        "currency": "INR",
        "subtotal": Decimal("1000.00"),
        "tax": Decimal("180.00"),
        "total": Decimal("1180.00"),
    }

    is_valid, errors = validate_invoice(invoice)

    assert is_valid is True
    assert errors == []
