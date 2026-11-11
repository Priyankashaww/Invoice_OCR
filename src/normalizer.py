# Normalizes dates, currencies and amounts
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation


class NormalizationError(ValueError):
    """Raised when OCR text cannot be safely normalized."""


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = re.sub(r"\s+", " ", str(value)).strip()
    return value or None


def normalize_invoice_number(value: str | None) -> str | None:
    value = normalize_text(value)
    return value.upper() if value else None


def normalize_vendor(value: str | None) -> str | None:
    return normalize_text(value)


def normalize_currency(value: str | None) -> str | None:
    value = normalize_text(value)
    if not value:
        return None

    value = value.upper().strip()
    symbol_map = {"₹": "INR", "€": "EUR", "£": "GBP"}
    value = symbol_map.get(value, value)

    if not re.fullmatch(r"[A-Z]{3}", value):
        raise NormalizationError(f"Unrecognized or ambiguous currency: {value}")

    return value


def normalize_date(value: str | None) -> str | None:
    """
    Return ISO YYYY-MM-DD.
    Ambiguous slash dates such as 04/05/2026 are rejected rather than guessed.
    """
    value = normalize_text(value)
    if not value:
        return None

    value = value.replace(",", "").strip()

    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%b-%Y",
        "%d %b %Y",
        "%d %B %Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass

    match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", value)
    if match:
        first, second, year = map(int, match.groups())
        if first > 12 and 1 <= second <= 12:
            return datetime(year, second, first).date().isoformat()
        if second > 12 and 1 <= first <= 12:
            return datetime(year, first, second).date().isoformat()
        raise NormalizationError(
            f"Ambiguous date '{value}': cannot determine day/month order"
        )

    raise NormalizationError(f"Invalid or unsupported invoice date: {value}")

def normalize_amount(value: str | Decimal | int | float | None) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        amount = value
    else:
        raw = str(value).strip()
        if not raw:
            return None
        raw = re.sub(r"(?i)\b(?:INR|USD|EUR|GBP|CAD|AUD)\b", "", raw)
        raw = re.sub(r"[₹]", "", raw)
        raw = re.sub(r"\s+", "", raw)

        if "," in raw and "." in raw:
            if not re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?", raw):
                raise NormalizationError(f"Ambiguous monetary format: {value}")
            raw = raw.replace(",", "")
        elif "," in raw:
            if re.fullmatch(r"-?\d{1,3}(,\d{3})+", raw):
                raw = raw.replace(",", "")
            else:
                raise NormalizationError(
                    f"Ambiguous monetary format: {value}"
                )

        if not re.fullmatch(r"-?\d+(?:\.\d{1,2})?", raw):
            raise NormalizationError(f"Invalid monetary amount: {value}")

        try:
            amount = Decimal(raw)
        except InvalidOperation as exc:
            raise NormalizationError(f"Invalid monetary amount: {value}") from exc

    return amount.quantize(Decimal("0.01"))
