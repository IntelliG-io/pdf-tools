"""Validation routines for pdf2docxplus."""
from __future__ import annotations

import logging
from pathlib import Path

from docx import Document
from pypdf import PdfReader

from .exceptions import ConversionError, InvalidPDFError
from .metadata import PDFMetadata
from .utils import to_path

LOGGER = logging.getLogger(__name__)


def validate_pdf(input_path: str | Path) -> None:
    """Validate that the provided PDF can be opened and parsed."""
    path = to_path(input_path)
    LOGGER.debug("Validating PDF input %s", path)
    try:
        PdfReader(str(path))
    except Exception as exc:  # pragma: no cover
        raise InvalidPDFError(f"Invalid or unreadable PDF: {path}") from exc


def validate_conversion(output_path: str | Path, metadata: PDFMetadata | None = None) -> None:
    """Validate that the converted DOCX is readable and optionally check metadata."""
    path = to_path(output_path)
    LOGGER.debug("Validating DOCX output %s", path)
    try:
        document = Document(str(path))
    except Exception as exc:  # pragma: no cover
        raise ConversionError(f"DOCX validation failed: {path}") from exc

    if metadata:
        core = document.core_properties
        if metadata.title and core.title != metadata.title:
            raise ConversionError("DOCX title metadata mismatch")
        if metadata.author and core.author != metadata.author:
            raise ConversionError("DOCX author metadata mismatch")
        if metadata.subject and core.subject != metadata.subject:
            raise ConversionError("DOCX subject metadata mismatch")
        if metadata.keywords and core.keywords != metadata.keywords:
            raise ConversionError("DOCX keywords metadata mismatch")
