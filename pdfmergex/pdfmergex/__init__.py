"""Top-level package for pdfmergex.

This package exposes utility functions for merging, validating, and
optimizing PDF documents. The public API is intentionally small to
keep the library easy to embed.
"""
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

__version__ = "0.1.0"
