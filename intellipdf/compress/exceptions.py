"""Custom exception types for the :mod:`intellipdf.compress` package."""

from __future__ import annotations


class PDFCompressXError(Exception):
    """Base exception for all :mod:`intellipdf.compress` related errors."""


class InvalidPDFError(PDFCompressXError):
    """Raised when a PDF file fails validation or is malformed."""


class CompressionError(PDFCompressXError):
    """Raised when compression fails or produces an invalid document."""
