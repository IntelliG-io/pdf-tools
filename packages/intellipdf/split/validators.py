"""Validation helpers for :mod:`intellipdf.split`."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from pypdf import PdfReader

from .exceptions import PDFValidationError
from .utils import coerce_path


def validate_pdf(path: str | Path) -> bool:
    """Validate that the given file is a readable PDF document."""

    pdf_path = coerce_path(path)
    if not pdf_path.exists():
        raise PDFValidationError(f"PDF file does not exist: {pdf_path}")
    if not pdf_path.is_file():
        raise PDFValidationError(f"PDF path is not a file: {pdf_path}")

    try:
        reader = PdfReader(str(pdf_path))
    except Exception as exc:  # pragma: no cover - defensive path
        raise PDFValidationError(f"Failed to read PDF: {pdf_path}") from exc

    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:  # pragma: no cover - optional behaviour
            raise PDFValidationError("Encrypted PDF requires a password") from exc

    num_pages = len(reader.pages)
    if num_pages == 0:
        raise PDFValidationError("PDF contains no pages")

    return True


def get_pdf_info(path: str | Path) -> Dict[str, Any]:
    """Return basic metadata about a PDF document."""

    pdf_path = coerce_path(path)
    reader = PdfReader(str(pdf_path))

    metadata = dict(reader.metadata or {})
    info: Dict[str, Any] = {
        "path": str(pdf_path),
        "pages": len(reader.pages),
        "is_encrypted": reader.is_encrypted,
        "metadata": metadata,
        "page_labels": list(getattr(reader, "page_labels", []) or []),
    }

    return info


__all__ = ["validate_pdf", "get_pdf_info"]
