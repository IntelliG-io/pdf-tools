"""Validation utilities for the :mod:`intellipdf.merge` package."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Any, Dict

from pypdf import PdfReader

from .exceptions import PdfValidationError
from .utils import PathLike, ensure_path

LOGGER = logging.getLogger("intellipdf.merge")


@dataclass(frozen=True)
class PDFInfo:
    """Summary information describing a PDF document."""

    path: Path
    num_pages: int
    is_encrypted: bool
    metadata: Dict[str, Any]


def validate_pdf(path: PathLike) -> bool:
    """Return ``True`` if *path* points to a valid, readable PDF.

    ``PdfValidationError`` is raised if the file cannot be read or does
    not contain any pages. Callers can rely on the return value being
    ``True`` if the function completes without error.
    """

    pdf_path = ensure_path(path)
    LOGGER.debug("Validating PDF at %s", pdf_path)
    try:
        reader = PdfReader(str(pdf_path))
    except Exception as exc:  # pragma: no cover - dependency exceptions vary
        LOGGER.error("Failed to read PDF %s: %s", pdf_path, exc)
        raise PdfValidationError(f"Unable to read PDF: {pdf_path}") from exc

    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:  # pragma: no cover
            LOGGER.error(
                "Encrypted PDF %s cannot be decrypted: %s", pdf_path, exc
            )
            raise PdfValidationError(
                "Encrypted PDF cannot be decrypted"
            ) from exc

    if len(reader.pages) == 0:
        LOGGER.error("PDF %s contains no pages", pdf_path)
        raise PdfValidationError("PDF contains no pages")

    LOGGER.info("Validated PDF %s successfully", pdf_path)
    return True


def get_pdf_info(path: PathLike) -> PDFInfo:
    """Return :class:`PDFInfo` describing the PDF located at *path*."""

    pdf_path = ensure_path(path)
    LOGGER.debug("Gathering PDF info for %s", pdf_path)
    validate_pdf(pdf_path)
    reader = PdfReader(str(pdf_path))

    metadata: Dict[str, Any] = {}
    if reader.metadata:
        metadata = {
            key: value
            for key, value in reader.metadata.items()
            if value is not None
        }

    info = PDFInfo(
        path=pdf_path,
        num_pages=len(reader.pages),
        is_encrypted=reader.is_encrypted,
        metadata=metadata,
    )
    LOGGER.info(
        "PDF info: path=%s, pages=%s, encrypted=%s",
        info.path,
        info.num_pages,
        info.is_encrypted,
    )
    return info


__all__ = ["validate_pdf", "get_pdf_info", "PDFInfo"]
