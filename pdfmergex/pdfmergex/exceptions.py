"""Custom exceptions for :mod:`pdfmergex`."""

from __future__ import annotations


class PdfMergeError(Exception):
    """Raised when the merge operation fails."""


class PdfValidationError(Exception):
    """Raised when a PDF file fails validation."""


class PdfOptimizationError(Exception):
    """Raised when optimization cannot be performed."""
