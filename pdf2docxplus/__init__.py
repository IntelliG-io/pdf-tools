"""Top-level package for pdf2docxplus.

This module exposes the public API for converting PDF documents to DOCX while
preserving layout, formatting, images, and metadata.
"""
from .converter import convert_pdf_to_docx
from .metadata import PDFMetadata, extract_metadata

__all__ = [
    "convert_pdf_to_docx",
    "extract_metadata",
    "PDFMetadata",
]

__version__ = "0.1.0"
