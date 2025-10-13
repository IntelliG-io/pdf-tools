"""Password protection helpers exposed through the IntelliPDF tools namespace."""

from __future__ import annotations

from .api import PdfSecurityError, is_pdf_encrypted, protect_pdf, unprotect_pdf

__all__ = [
    "PdfSecurityError",
    "protect_pdf",
    "unprotect_pdf",
    "is_pdf_encrypted",
]
