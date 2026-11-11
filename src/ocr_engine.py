# Runs Tesseract on images

from pathlib import Path

import pytesseract
from PIL import Image, ImageOps, ImageEnhance


def configure_tesseract(executable_path: str | None = None) -> None:
    """Configure Tesseract. PATH is used when executable_path is omitted."""
    if executable_path:
        pytesseract.pytesseract.tesseract_cmd = executable_path


def extract_text(image_path: str | Path) -> str:
    """Run local Tesseract OCR on an image and return the recognized text."""
    image_path = Path(image_path)

    with Image.open(image_path) as original:
        image = ImageOps.exif_transpose(original).convert("L")
        image = ImageOps.autocontrast(image)
        image = ImageEnhance.Contrast(image).enhance(1.5)

        image = image.resize(
            (image.width * 2, image.height * 2),
            Image.Resampling.LANCZOS,
        )

        text = pytesseract.image_to_string(
            image,
            lang="eng",
            config="--oem 3 --psm 6",
        )

    return text.strip()
