"""Compression utilities exposed through the IntelliPDF tools namespace."""

from __future__ import annotations

from .compressor import (
    CompressionLevel,
    CompressionResult,
    compress_pdf,
)
from .exceptions import CompressionError, InvalidPDFError, PDFCompressXError
from .info import CompressionInfo, get_compression_info
from .validators import validate_pdf

__all__ = [
    "CompressionLevel",
    "CompressionResult",
    "CompressionInfo",
    "compress_pdf",
    "get_compression_info",
    "validate_pdf",
    "CompressionError",
    "InvalidPDFError",
    "PDFCompressXError",
]
