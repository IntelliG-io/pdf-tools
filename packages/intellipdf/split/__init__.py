"""Split utilities for the :mod:`intellipdf` toolkit."""

from __future__ import annotations

from .exceptions import IntelliPDFSplitError, InvalidPageRangeError, PDFValidationError
from .optimizers import optimize_pdf
from .splitter import extract_pages, split_pdf
from .utils import PageRange, build_output_filename, normalize_pages, parse_page_ranges
from .validators import get_pdf_info, validate_pdf

__all__ = [
    "split_pdf",
    "extract_pages",
    "get_pdf_info",
    "validate_pdf",
    "optimize_pdf",
    "IntelliPDFSplitError",
    "InvalidPageRangeError",
    "PDFValidationError",
    "PageRange",
    "build_output_filename",
    "normalize_pages",
    "parse_page_ranges",
]
