"""Merge utilities for the :mod:`intellipdf` toolkit."""

from __future__ import annotations

from .exceptions import PdfMergeError, PdfOptimizationError, PdfValidationError
from .merger import merge_pdfs
from .optimizers import optimize_pdf
from .validators import PDFInfo, get_pdf_info, validate_pdf

__all__ = [
    "merge_pdfs",
    "validate_pdf",
    "get_pdf_info",
    "optimize_pdf",
    "PdfMergeError",
    "PdfValidationError",
    "PdfOptimizationError",
    "PDFInfo",
]
