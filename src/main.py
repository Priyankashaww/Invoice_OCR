# CLI entry point and arguments
import argparse
import json
from pathlib import Path

from .ocr_engine import configure_tesseract
from .processor import process_directory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract, validate and store invoice data from image files."
    )
    parser.add_argument("--data", default="data", help="Directory containing invoice images")
    parser.add_argument("--result", default="result", help="Directory for OCR text and JSON reports")
    parser.add_argument("--db", default="db/invoices.db", help="SQLite database path")
    parser.add_argument(
        "--tesseract",
        default=None,
        help="Optional full path to tesseract.exe (useful on Windows)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    configure_tesseract(args.tesseract)

    try:
        report = process_directory(args.data, args.result, args.db)
    except Exception as exc:
        print(f"Application error: {type(exc).__name__}: {exc}")
        return 1

    print("\n------------- INVOICE OCR PROCESSOR --------------")
    print(f"Input directory : {Path(args.data).resolve()}")
    for record in report["records"]:
        print(f"{record['source_filename']}: {record['status'].upper()}")
        for reason in record.get("review_reasons", []):
            print(f"    - {reason}")

    print("\n--------------- SUMMARY -------------------")
    for key, value in report["summary"].items():
        print(f"{key.replace('_', ' ').title():18}: {value}")
    print(f"Database         : {Path(args.db).resolve()}")
    print(f"Records report   : {(Path(args.result) / 'extracted_records.json').resolve()}")
    print(f"Review report    : {(Path(args.result) / 'review_report.json').resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
