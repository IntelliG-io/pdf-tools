"""Custom exceptions for pdf2docxplus."""
from __future__ import annotations


class Pdf2DocxPlusError(RuntimeError):
    """Base class for all pdf2docxplus exceptions."""


class InvalidPDFError(Pdf2DocxPlusError):
    """Raised when the provided PDF document is invalid or unreadable."""


class ConversionError(Pdf2DocxPlusError):
    """Raised when a conversion error occurs."""


class MetadataError(Pdf2DocxPlusError):
    """Raised when metadata extraction or application fails."""
