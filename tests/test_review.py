from src.validator import validate_invoice
from src.normalizer import normalize_date, NormalizationError


def test_incomplete_invoice():
    invoice = {
        "invoice": None,
        "vendor": "ABC Technologies",
        "date": None,
        "currency": "INR",
        "subtotal": "1000.00",
        "tax": None,
        "total": "1180.00",
    }

    is_valid, errors = validate_invoice(invoice)

    assert is_valid is False
    assert "Missing invoice_number" in errors
    assert "Missing invoice_date" in errors
    assert "Missing tax" in errors


def test_ambiguous_date_is_rejected():
    try:
        normalize_date("04/05/2026")
    except NormalizationError as exc:
        assert "Ambiguous date" in str(exc)
    else:
        raise AssertionError("Ambiguous date should not be guessed")
