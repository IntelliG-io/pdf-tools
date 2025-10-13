"""Split utilities exposed through the IntelliPDF tools namespace."""

from __future__ import annotations

from . import split as splitter
from .exceptions import IntelliPDFSplitError, InvalidPageRangeError, PDFValidationError
from .operations import extract_pages, split_pdf
from .optimizers import optimize_pdf
from .utils import PageRange, build_output_filename, normalize_pages, parse_page_ranges
from .validators import get_pdf_info, validate_pdf

# Ensure the module alias exposes optimization helpers for tests and legacy callers.
setattr(splitter, "optimize_pdf", optimize_pdf)

__all__ = [
    "split_pdf",
    "extract_pages",
    "get_pdf_info",
    "validate_pdf",
    "optimize_pdf",
    "PageRange",
    "normalize_pages",
    "parse_page_ranges",
    "build_output_filename",
    "InvalidPageRangeError",
    "IntelliPDFSplitError",
    "PDFValidationError",
    "splitter",
]
