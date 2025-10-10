"""
Custom exceptions for PDF Splitter.

This module defines all custom exceptions used throughout the library.
"""


class PDFSplitterException(Exception):
    """Base exception for all PDF Splitter errors."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message or self.default_message)
        self.message = message or self.default_message

    @property
    def default_message(self) -> str:
        return "An unknown PDF splitter error occurred."


class InvalidPDFError(PDFSplitterException):
    """Raised when PDF file is invalid or corrupted."""

    @property
    def default_message(self) -> str:
        return "Invalid or corrupted PDF file."


class EncryptedPDFError(PDFSplitterException):
    """Raised when PDF is encrypted and cannot be processed."""

    @property
    def default_message(self) -> str:
        return "PDF is encrypted and cannot be processed without a password."


class InvalidRangeError(PDFSplitterException):
    """Raised when page range specification is invalid."""

    @property
    def default_message(self) -> str:
        return "Invalid page range specification."


class PageOutOfBoundsError(PDFSplitterException):
    """Raised when requested page number is out of bounds."""

    @property
    def default_message(self) -> str:
        return "Requested page number is out of bounds."


class InsufficientDiskSpaceError(PDFSplitterException):
    """Raised when there's insufficient disk space for operation."""

    @property
    def default_message(self) -> str:
        return "Insufficient disk space for PDF operation."
