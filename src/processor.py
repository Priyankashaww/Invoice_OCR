# Coordinates the complete pipeline
import hashlib
import json
from pathlib import Path
from decimal import Decimal

from .ocr_engine import extract_text
from .extractor import extract_invoice_fields
from .normalizer import (
    normalize_invoice_number, normalize_vendor, normalize_date,
    normalize_currency, normalize_amount, NormalizationError,
)
from .validator import validate_invoice
from .database import (
    initialize_database, save_valid_invoice, save_nonvalid_source,
)


SUPPORTED_EXTENSIONS = {".png"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_safe(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def normalize_fields(fields: dict) -> tuple[dict, list[str]]:
    normalized = {}
    errors = []

    normalizers = {
        "invoice": normalize_invoice_number,
        "vendor": normalize_vendor,
        "date": normalize_date,
        "currency": normalize_currency,
        "subtotal": normalize_amount,
        "tax": normalize_amount,
        "total": normalize_amount,
    }

    for field, normalizer in normalizers.items():
        try:
            normalized[field] = normalizer(fields.get(field))
        except NormalizationError as exc:
            normalized[field] = None
            errors.append(f"{field}: {exc}")

    return normalized, errors


def process_directory(
    data_dir: str | Path,
    result_dir: str | Path,
    db_path: str | Path,
) -> dict:
    data_dir = Path(data_dir)
    result_dir = Path(result_dir)
    raw_dir = result_dir / "raw_ocr"
    raw_dir.mkdir(parents=True, exist_ok=True)

    if not data_dir.exists() or not data_dir.is_dir():
        raise FileNotFoundError(f"Input directory does not exist: {data_dir}")

    initialize_database(db_path)

    image_files = sorted(
        path for path in data_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    results = []

    for image_path in image_files:
        filename = image_path.name
        file_hash = ""
        raw_path = raw_dir / f"{image_path.stem}.txt"
        try:
            file_hash = sha256_file(image_path)
            ocr_text = extract_text(image_path)
            raw_path.write_text(ocr_text, encoding="utf-8")

            extracted = extract_invoice_fields(ocr_text)
            normalized, normalization_errors = normalize_fields(extracted)
            is_valid, validation_errors = validate_invoice(normalized)
            reasons = normalization_errors + validation_errors

            record = {
                "source_filename": filename,
                "file_hash": file_hash,
                "ocr_text_path": str(raw_path),
                "extracted_fields": _json_safe(normalized),
                "validation_errors": reasons,
            }

            if reasons or not is_valid:
                status = "needs_review"
                save_nonvalid_source(
                    db_path, filename, file_hash, str(raw_path),
                    status, reasons,
                )
                record["status"] = status
                record["review_reasons"] = reasons
            else:
                status, invoice_id, duplicate_reasons = save_valid_invoice(
                    db_path, normalized, filename, file_hash, str(raw_path)
                )
                record["status"] = status
                record["invoice_id"] = invoice_id
                record["review_reasons"] = duplicate_reasons
                if status == "needs_review":
                    record["validation_errors"] = duplicate_reasons

            results.append(record)

        except Exception as exc:
            reason = f"{type(exc).__name__}: {exc}"
            try:
                if not file_hash:
                    file_hash = sha256_file(image_path)
                save_nonvalid_source(
                    db_path, filename, file_hash,
                    str(raw_path) if raw_path.exists() else None,
                    "failed", [reason],
                )
            except Exception as db_exc:
                reason += f"; additionally failed to record source: {db_exc}"

            results.append({
                "source_filename": filename,
                "file_hash": file_hash or None,
                "ocr_text_path": str(raw_path) if raw_path.exists() else None,
                "status": "failed",
                "extracted_fields": {},
                "validation_errors": [reason],
                "review_reasons": [reason],
            })

    counts = {
        "total_files": len(results),
        "valid_invoices": sum(r["status"] == "valid" for r in results),
        "duplicates": sum(r["status"] == "duplicate" for r in results),
        "needs_review": sum(r["status"] == "needs_review" for r in results),
        "failed": sum(r["status"] == "failed" for r in results),
    }

    report = {"summary": counts, "records": results}
    review_report = {
        "needs_review": [
            r for r in results if r["status"] in {"needs_review", "failed"}
        ]
    }

    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / "extracted_records.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (result_dir / "review_report.json").write_text(
        json.dumps(review_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return report

