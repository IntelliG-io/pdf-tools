"""Custom exceptions raised by :mod:`pdfsplitx`."""

from __future__ import annotations

from typing import Iterable


class PDFSplitXError(Exception):
    """Base exception for all errors raised by :mod:`pdfsplitx`."""


class PDFValidationError(PDFSplitXError):
    """Raised when validation of a PDF file fails."""


class InvalidPageRangeError(PDFSplitXError):
    """Raised when the provided page ranges cannot be parsed or validated."""

    def __init__(self, ranges: Iterable[object]) -> None:
        self.ranges = list(ranges)
        message = f"Invalid or empty page ranges provided: {self.ranges!r}"
        super().__init__(message)
