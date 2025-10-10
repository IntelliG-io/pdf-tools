"""Utility functions for PDF operations."""

from __future__ import annotations

import os
from typing import Optional, Tuple

from .document import PDFDocumentAdapter
from .exceptions import (
    EncryptedPDFError,
    InvalidPDFError,
    PDFSplitterException,
)
from .types import PDFInfo


def get_pdf_info(pdf_path: str, password: Optional[str] = None) -> PDFInfo:
    """Return rich information about a PDF document using :class:`PDFInfo`."""

    adapter = PDFDocumentAdapter(pdf_path, password=password)
    return adapter.to_pdf_info()


def validate_pdf(pdf_path: str, password: Optional[str] = None) -> Tuple[bool, str]:
    """Perform lightweight validation of a PDF file."""

    if not os.path.exists(pdf_path):
        return False, f"File not found: {pdf_path}"

    if not os.path.isfile(pdf_path):
        return False, f"Path is not a file: {pdf_path}"

    if not pdf_path.lower().endswith(".pdf"):
        return False, f"File does not have .pdf extension: {pdf_path}"

    if not os.access(pdf_path, os.R_OK):
        return False, f"Cannot read file (permission denied): {pdf_path}"

    try:
        adapter = PDFDocumentAdapter(pdf_path, password=password)
        adapter.validate_access()
        return True, ""
    except EncryptedPDFError as exc:
        return False, str(exc)
    except InvalidPDFError as exc:
        return False, str(exc)
    except PDFSplitterException as exc:
        return False, str(exc)
    except Exception as exc:  # pragma: no cover - defensive
        return False, f"Unexpected error reading PDF: {exc}"


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        Formatted string (e.g., "1.5 MB", "500 KB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"
