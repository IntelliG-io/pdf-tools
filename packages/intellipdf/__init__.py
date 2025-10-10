"""Unified PDF processing toolkit exposing split, merge, and compression helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

from . import compress, merge, split
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
from .split import (
    extract_pages,
    split_pdf,
    validate_pdf as validate_split_pdf,
    get_pdf_info as get_split_info,
)
from .split.optimizers import optimize_pdf as optimize_split_pdf

__all__ = [
    "compress",
    "merge",
    "split",
    "split_pdf",
    "extract_pages",
    "merge_pdfs",
    "compress_pdf",
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
