"""Unified PDF processing toolkit exposing split, merge, compression, PDF→DOCX and security helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

from . import compress, merge, security,pdf2docx , split
from .compress import (
    CompressionError,
    CompressionInfo,
    CompressionLevel,
    CompressionResult,
    InvalidPDFError,
    PDFCompressXError,
    compress_pdf,
    get_compression_info,
    validate_pdf as validate_compression_pdf,
)
from .merge import (
    PDFInfo,
    PdfMergeError,
    PdfOptimizationError,
    PdfValidationError,
    merge_pdfs,
    optimize_pdf as optimize_merge_pdf,
    validate_pdf as validate_merge_pdf,
    get_pdf_info as get_merge_info,
)
from .security import (
    PdfSecurityError,
    is_pdf_encrypted,
    protect_pdf,
    unprotect_pdf,
)
from .split import (
    extract_pages,
    split_pdf,
    validate_pdf as validate_split_pdf,
    get_pdf_info as get_split_info,
)
from .split.optimizers import optimize_pdf as optimize_split_pdf
from .pdf2docx import (
    ConversionMetadata,
    ConversionOptions,
    ConversionResult,
    PdfToDocxConverter,
    convert_pdf_to_docx,
)

__all__ = [
    "compress",
    "merge",
    "split",
    "pdf2docx",
    "security",
    "split_pdf",
    "extract_pages",
    "merge_pdfs",
    "compress_pdf",
    "protect_pdf",
    "unprotect_pdf",
    "is_pdf_encrypted",
    "protect_document",
    "unprotect_document",
    "is_document_encrypted",
    "get_split_info",
    "get_merge_info",
    "get_compression_info",
    "validate_split_pdf",
    "validate_merge_pdf",
    "validate_compression_pdf",
    "optimize_split_pdf",
    "optimize_merge_pdf",
    "CompressionLevel",
    "CompressionResult",
    "CompressionInfo",
    "CompressionError",
    "InvalidPDFError",
    "PDFCompressXError",
    "PdfMergeError",
    "PdfValidationError",
    "PdfOptimizationError",
    "PDFInfo",
    "convert_pdf_to_docx",
    "PdfToDocxConverter",
    "ConversionOptions",
    "ConversionMetadata",
    "ConversionResult",
    "convert_document",
    "PdfSecurityError",
]


def split_document(
    input: str | Path,
    output_dir: str | Path,
    *,
    mode: str = "range",
    ranges: str | Sequence[object] | None = None,
    pages: Sequence[int | str] | None = None,
) -> list[Path]:
    """Convenience wrapper around :func:`split.split_pdf`."""

    return split_pdf(input, output_dir, mode=mode, ranges=ranges, pages=pages)


def extract_document_pages(
    input: str | Path,
    page_numbers: Sequence[int | str],
    output: str | Path,
) -> Path:
    """Convenience wrapper around :func:`split.extract_pages`."""

    return extract_pages(input, page_numbers, output)


def merge_documents(inputs: Iterable[str | Path], output: str | Path) -> Path:
    """Convenience wrapper around :func:`merge.merge_pdfs`."""

    return merge_pdfs(inputs, output)


def compress_document(
    input: str | Path,
    output: str | Path,
    *,
    level: CompressionLevel | None = None,
) -> CompressionResult:
    """Convenience wrapper around :func:`compress.compress_pdf`."""

    return compress_pdf(input, output, level=level)


def convert_document(
    input: str | Path | pdf2docx.PdfDocument,
    output: str | Path | None = None,
    *,
    options: ConversionOptions | None = None,
    metadata: ConversionMetadata | None = None,
) -> ConversionResult:
    """Convenience wrapper for PDF → DOCX conversion."""

    return convert_pdf_to_docx(input, output, options=options, metadata=metadata)
def protect_document(
    input: str | Path,
    output: str | Path,
    password: str,
    *,
    owner_password: str | None = None,
) -> Path:
    """Convenience wrapper around :func:`security.protect_pdf`."""

    return protect_pdf(
        input,
        output,
        password,
        owner_password=owner_password,
    )


def unprotect_document(input: str | Path, output: str | Path, password: str) -> Path:
    """Convenience wrapper around :func:`security.unprotect_pdf`."""

    return unprotect_pdf(input, output, password)


def is_document_encrypted(path: str | Path) -> bool:
    """Convenience wrapper around :func:`security.is_pdf_encrypted`."""

    return is_pdf_encrypted(path)
