# SQLite connection and CRUD operations
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

db_path ="C:/TNM_Project/db/"
def connect(db_path: str | Path) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(db_path: str | Path) -> None:
    with connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice TEXT NOT NULL,
                vendor TEXT NOT NULL,
                vendor_key TEXT NOT NULL,
                date TEXT NOT NULL,
                currency TEXT NOT NULL,
                subtotal TEXT NOT NULL,
                tax TEXT NOT NULL,
                total TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(vendor_key, invoice)
            );

            CREATE TABLE IF NOT EXISTS invoice_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NULL,
                source_filename TEXT NOT NULL UNIQUE,
                file_hash TEXT NOT NULL,
                ocr_text_path TEXT,
                processing_status TEXT NOT NULL,
                review_reasons TEXT NOT NULL DEFAULT '[]',
                processed_at TEXT NOT NULL,
                FOREIGN KEY(invoice_id) REFERENCES invoices(id)
            );
            """
        )


def _vendor_key(vendor: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]", "", vendor.casefold())


def _same_invoice(existing: sqlite3.Row, invoice: dict) -> bool:
    fields = (
        "vendor", "date", "currency",
        "subtotal", "tax", "total",
    )
    return all(str(existing[field]) == str(invoice[field]) for field in fields)


def save_valid_invoice(
    db_path: str | Path,
    invoice: dict,
    source_filename: str,
    file_hash: str,
    ocr_text_path: str | None,
) -> tuple[str, int | None, list[str]]:
    """
    Insert a new invoice or link a repeated scan to an existing invoice.
    A conflicting scan with the same vendor+invoice number is flagged for review.
    """
    now = datetime.now(timezone.utc).isoformat()
    vendor_key = _vendor_key(invoice["vendor"])
    reasons: list[str] = []

    with connect(db_path) as conn:
        conn.execute("BEGIN")
        existing = conn.execute(
            """
            SELECT * FROM invoices
            WHERE vendor_key = ? AND invoice = ?
            """,
            (vendor_key, invoice["invoice"]),
        ).fetchone()

        if existing is None:
            cursor = conn.execute(
                """
                INSERT INTO invoices (
                    invoice, vendor, vendor_key, date,
                    currency, subtotal, tax, total, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    invoice["invoice"], invoice["vendor"], vendor_key,
                    invoice["date"], invoice["currency"],
                    str(invoice["subtotal"]), str(invoice["tax"]),
                    str(invoice["total"]), now,
                ),
            )
            invoice_id = cursor.lastrowid
            status = "valid"
        else:
            invoice_id = existing["id"]
            if _same_invoice(existing, invoice):
                status = "duplicate"
            else:
                status = "needs_review"
                reasons.append(
                    "Conflicting data found for an existing vendor and invoice number"
                )

        conn.execute(
            """
            INSERT INTO invoice_sources (
                invoice_id, source_filename, file_hash, ocr_text_path,
                processing_status, review_reasons, processed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_filename) DO UPDATE SET
                invoice_id = excluded.invoice_id,
                file_hash = excluded.file_hash,
                ocr_text_path = excluded.ocr_text_path,
                processing_status = excluded.processing_status,
                review_reasons = excluded.review_reasons,
                processed_at = excluded.processed_at
            """,
            (
                invoice_id, source_filename, file_hash, ocr_text_path,
                status, json.dumps(reasons), now,
            ),
        )

    return status, invoice_id, reasons


def save_nonvalid_source(
    db_path: str | Path,
    source_filename: str,
    file_hash: str,
    ocr_text_path: str | None,
    status: str,
    reasons: list[str],
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO invoice_sources (
                invoice_id, source_filename, file_hash, ocr_text_path,
                processing_status, review_reasons, processed_at
            ) VALUES (NULL, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_filename) DO UPDATE SET
                invoice_id = NULL,
                file_hash = excluded.file_hash,
                ocr_text_path = excluded.ocr_text_path,
                processing_status = excluded.processing_status,
                review_reasons = excluded.review_reasons,
                processed_at = excluded.processed_at
            """,
            (
                source_filename, file_hash, ocr_text_path, status,
                json.dumps(reasons), now,
            ),
        )


def get_invoice_count(db_path: str | Path) -> int:
    with connect(db_path) as conn:
        return conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]


def get_source_count(db_path: str | Path) -> int:
    with connect(db_path) as conn:
        return conn.execute("SELECT COUNT(*) FROM invoice_sources").fetchone()[0]
