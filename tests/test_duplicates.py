from decimal import Decimal

from src.database import (
    initialize_database, save_valid_invoice,
    get_invoice_count, get_source_count,
)


def test_duplicate_repeated_import_is_idempotent(tmp_path):
    db_path = tmp_path / "test_invoices.db"
    initialize_database(db_path)

    invoice = {
        "invoice": "INV-101",
        "vendor": "ABC Technologies",
        "date": "2026-11-10",
        "currency": "INR",
        "subtotal": Decimal("1000.00"),
        "tax": Decimal("180.00"),
        "total": Decimal("1180.00"),
    }

    first_status, first_id, _ = save_valid_invoice(
        db_path, invoice, "invoice-101.png", "hash-a", "raw/invoice-101.txt"
    )
    second_status, second_id, _ = save_valid_invoice(
        db_path, invoice, "invoice-101.png", "hash-a", "raw/invoice-101.txt"
    )
    copy_status, copy_id, _ = save_valid_invoice(
        db_path, invoice, "invoice-101-copy.png", "hash-b", "raw/invoice-101-copy.txt"
    )

    assert first_status == "valid"
    assert second_status == "duplicate"
    assert copy_status == "duplicate"
    assert first_id == second_id == copy_id
    assert get_invoice_count(db_path) == 1
    assert get_source_count(db_path) == 2
