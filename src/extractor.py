# Extracts invoice fields from OCR text

import re
from typing import Optional


def _clean_value(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" \t:|-")


def _find_label_value(text: str, labels: list[str]) -> Optional[str]:
    """
    Find a value on the same line as a known label.
    Anchoring to the beginning of a line reduces accidental matches,
    especially Total matching Subtotal.
    """
    label_pattern = "|".join(
        rf"(?:{label})" for label in labels
    )
    pattern = re.compile(
        rf"^\s*(?:{label_pattern})\s*(?:[:#\-]\s*)?(.+?)\s*$",
        re.IGNORECASE | re.MULTILINE,
    )

    matches = pattern.findall(text)
    for value in matches:
        value = _clean_value(value)
        if value:
            return value
    return None


def extract_invoice_fields(ocr_text: str) -> dict:
    """Extract candidate fields from OCR text. Values remain untrusted strings."""
    invoice = _find_label_value(
        ocr_text,
        [
            r"invoice\s*(?:number|no\.?|#)",
            r"inv\.?\s*(?:number|no\.?|#)",
        ],
    )

    vendor = _find_label_value(
        ocr_text,
        [r"vendor", r"supplier", r"seller", r"issued\s+by"],
    )

    date = _find_label_value(
        ocr_text,
        [r"invoice\s+date", r"date\s+of\s+invoice", r"date"],
    )

    currency = _find_label_value(
        ocr_text,
        [r"currency"],
    )

    subtotal = _find_label_value(
        ocr_text,
        [r"sub\s*total", r"subtotal"],
    )

    tax = _find_label_value(
        ocr_text,
        [r"tax\s*(?:amount)?", r"gst", r"vat"],
    )

    total = _find_label_value(
        ocr_text,
        [r"grand\s+total", r"invoice\s+total", r"total\s+due", r"total"],
    )

    if not currency:
        if re.search(r"₹", ocr_text):
            currency = "INR"
        elif re.search(r"€", ocr_text):
            currency = "EUR"
        elif re.search(r"£", ocr_text):
            currency = "GBP"

    return {
        "invoice": invoice,
        "vendor": vendor,
        "date": date,
        "currency": currency,
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
    }
