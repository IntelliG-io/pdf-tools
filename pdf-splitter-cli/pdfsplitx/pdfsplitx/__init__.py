"""Top-level package for the :mod:`pdfsplitx` library."""

from __future__ import annotations

from .splitter import split_pdf, extract_pages
from .validators import get_pdf_info, validate_pdf

__all__ = [
    "split_pdf",
    "extract_pages",
    "get_pdf_info",
    "validate_pdf",
]

__version__ = "0.1.0"
