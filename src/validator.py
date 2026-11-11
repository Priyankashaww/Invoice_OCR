# Checks fields and arithmetic
from decimal import Decimal, InvalidOperation
import re


ALIASES = {
    "invoice": ("invoice_number", "invoice"),
    "date": ("invoice_date", "date"),
}


def _value(invoice: dict, canonical: str):
    for key in ALIASES.get(canonical, (canonical,)):
        if invoice.get(key) is not None and str(invoice.get(key)).strip():
            return invoice.get(key)
    return None


def validate_invoice(invoice: dict) -> tuple[bool, list[str]]:
    """Validate a normalized invoice. Returns (is_valid, list_of_errors)."""
    errors: list[str] = []

    required = [
        "invoice",
        "vendor",
        "date",
        "currency",
        "subtotal",
        "tax",
        "total",
    ]

    values = {field: _value(invoice, field) for field in required}

    for field, value in values.items():
        if value is None or (isinstance(value, str) and not value.strip()):
            errors.append(f"Missing {field}")

    currency = values["currency"]
    if currency is not None and not re.fullmatch(
        r"[A-Z]{3}", str(currency).strip().upper()
    ):
        errors.append("Invalid currency code")

    amounts = {}
    for field in ("subtotal", "tax", "total"):
        value = values[field]
        if value is None:
            continue
        try:
            amounts[field] = Decimal(str(value))
        except (InvalidOperation, ValueError):
            errors.append(f"Invalid {field} amount")

    for field, amount in amounts.items():
        if amount < 0:
            errors.append(f"{field} cannot be negative")

    if all(field in amounts for field in ("subtotal", "tax", "total")):
        if amounts["subtotal"] + amounts["tax"] != amounts["total"]:
            errors.append("Subtotal + tax does not equal total")

    date_value = values["date"]
    if date_value is not None:
        try:
            from datetime import date
            date.fromisoformat(str(date_value))
        except ValueError:
            errors.append("Invoice date must be normalized to YYYY-MM-DD")

    return len(errors) == 0, errors
