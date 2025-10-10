"""Custom exceptions for the :mod:`intellipdf.merge` package."""

from __future__ import annotations


class PdfMergeError(Exception):
    """Raised when the merge operation fails."""


class PdfValidationError(Exception):
    """Raised when a PDF file fails validation."""


class PdfOptimizationError(Exception):
    """Raised when optimization cannot be performed."""
