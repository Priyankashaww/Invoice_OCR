# Invoice OCR Processing System

## Overview

A Python CLI application that extracts invoice information from images using local OCR, validates records and stores valid invoices in SQLite.

## Features

- Local OCR using Tesseract
- Invoice field extraction
- Date and monetary normalization
- Decimal-based financial calculations
- Invoice validation
- Duplicate detection
- SQLite persistence
- Source scan traceability
- Needs-review reporting
- Error handling per image
- Automated tests

## Download and install tesseract at first

https://sourceforge.net/projects/tesseract-ocr.mirror/

## Requirements

Python 3.11+
Tesseract OCR

## Installation

pip install -r req.txt

## Tests

pytest -v

## Usage/Run

python -m src.main --data data --result result --db db/invoices.db

## Database Design

Explain invoices and invoice_sources tables.

## Duplicate Handling

Explain vendor_key + invoice_number.

## Output

Explain generated JSON reports.

result/raw_ocr/\*.txt: raw OCR text for each successfully OCR-processed image.
result/extracted_records.json: all processing records and summary counts.
result/review_report.json: records requiring review or marked failed.
db/invoices.db: valid invoices and source scan associations.

## Limitations

Document OCR accuracy and ambiguous
date/currency handling.
OCR is imperfect.
The application does not infer missing fields. Slash-formatted dates such as 04/05/2026 are treated as ambiguous unless the date order is clear. A dollar symbol alone does not identify a unique currency. Unrecognized formats are sent to review rather than guessed.
The initial extractor uses common invoice labels. If the supplied fixtures use different labels or layouts, inspect result/raw_ocr/\*.txt and extend the label patterns in src/extractor.py. The raw OCR text remains available for auditing.
