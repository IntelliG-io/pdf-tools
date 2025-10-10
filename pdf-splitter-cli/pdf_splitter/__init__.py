"""
PDF Splitter - Comprehensive library for splitting PDF files.

This library provides a clean, intuitive API for splitting PDF files into
individual pages, ranges, chunks, or extracting specific pages. It also
supports batch processing of multiple PDFs.

Quick Start:
    >>> from pdf_splitter import PDFSplitter
    >>> splitter = PDFSplitter('input.pdf')
    >>> files = splitter.split_to_pages('output/')

Main Classes:
    - PDFSplitter: Main class for all splitting operations
    - BatchProcessor: Process multiple PDFs at once

Data Classes:
    - PDFInfo: PDF metadata and information
    - SplitResult: Result of split operation
    - BatchResult: Result of batch operation

Exceptions:
    - PDFSplitterException: Base exception
    - InvalidPDFError: Invalid or corrupted PDF
    - EncryptedPDFError: Encrypted PDF
    - InvalidRangeError: Invalid page range
    - PageOutOfBoundsError: Page number out of bounds

Utility Functions:
    - get_pdf_info: Get PDF metadata and information
    - validate_pdf: Validate PDF file
    - format_file_size: Format file size in human-readable format

For CLI usage, use the 'pdf-splitter' command after installation.
"""

# Core classes
from pdf_splitter.splitter import PDFSplitter, BatchProcessor

# Data types
from pdf_splitter.types import PDFInfo, SplitResult, BatchResult

# Exceptions
from pdf_splitter.exceptions import (
    PDFSplitterException,
    InvalidPDFError,
    EncryptedPDFError,
    InvalidRangeError,
    PageOutOfBoundsError,
    InsufficientDiskSpaceError,
)

# Utility functions
from pdf_splitter.utils import get_pdf_info, validate_pdf, format_file_size

__version__ = "1.0.0"
__author__ = "PDF Splitter CLI Contributors"
__license__ = "MIT"

__all__ = [
    # Main classes
    "PDFSplitter",
    "BatchProcessor",
    # Data types
    "PDFInfo",
    "SplitResult",
    "BatchResult",
    # Exceptions
    "PDFSplitterException",
    "InvalidPDFError",
    "EncryptedPDFError",
    "InvalidRangeError",
    "PageOutOfBoundsError",
    "InsufficientDiskSpaceError",
    # Utility functions
    "get_pdf_info",
    "validate_pdf",
    "format_file_size",
    # Version info
    "__version__",
]
