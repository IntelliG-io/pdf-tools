"""Unified PDF processing toolkit exposing modular IntelliPDF tools."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, Sequence

from .exporters.docx import DocxGenerator, DocxGenerationResult, DocxGenerationStats, generate_docx
from .tools import compressor as compress
from .tools import encryptor as security
from .tools import merger as merge
from .tools import splitter as split
from .tools.converter import pdf_to_docx
from .tools.compressor import (
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
from .tools.converter.pdf_to_docx import ConversionMetadata, ConversionOptions, ConversionResult, PdfToDocxConverter
from .tools.encryptor import (
    PdfSecurityError,
    is_pdf_encrypted,
    protect_pdf,
    unprotect_pdf,
)
from .tools.merger import (
    PDFInfo,
    PdfMergeError,
    PdfOptimizationError,
    PdfValidationError,
    merge_pdfs,
    optimize_pdf as optimize_merge_pdf,
    validate_pdf as validate_merge_pdf,
    get_pdf_info as get_merge_info,
)
from .tools.splitter import (
    extract_pages,
    split_pdf,
    validate_pdf as validate_split_pdf,
    get_pdf_info as get_split_info,
)
from .tools.splitter.optimizers import optimize_pdf as optimize_split_pdf
from .tools import load_builtin_plugins
from .tools.common.interfaces import ConversionContext
from .tools.common.pipeline import ToolRegistry, register_tool, registry
from .converter import ConversionPipeline, convert_pdf_to_docx

pdf2docx = pdf_to_docx

load_builtin_plugins()

# Backwards-compatible module aliases for deprecated top-level packages.
sys.modules.setdefault(__name__ + ".compress", compress)
sys.modules.setdefault(__name__ + ".merge", merge)
sys.modules.setdefault(__name__ + ".split", split)
sys.modules.setdefault(__name__ + ".security", security)
sys.modules.setdefault(__name__ + ".pdf2docx", pdf2docx)

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
    "ConversionContext",
    "ToolRegistry",
    "registry",
    "register_tool",
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
    "ConversionPipeline",
    "DocxGenerator",
    "DocxGenerationResult",
    "DocxGenerationStats",
    "generate_docx",
    "ConversionContext",
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
    """Convenience wrapper around the split plugin."""

    context = ConversionContext(
        input_path=input,
        output_path=output_dir,
        config={"mode": mode, "ranges": ranges, "pages": pages},
    )
    tool = registry.create("split", context)
    return tool.run()


def extract_document_pages(
    input: str | Path,
    page_numbers: Sequence[int | str],
    output: str | Path,
) -> Path:
    """Convenience wrapper around the extract plugin."""

    context = ConversionContext(
        input_path=input,
        output_path=output,
        config={"pages": page_numbers},
    )
    tool = registry.create("extract", context)
    return tool.run()


def merge_documents(inputs: Iterable[str | Path], output: str | Path, **config) -> Path:
    """Convenience wrapper around the merge plugin."""

    context = ConversionContext(output_path=output, config={"inputs": list(inputs), **config})
    tool = registry.create("merge", context)
    return tool.run()


def compress_document(
    input: str | Path,
    output: str | Path,
    *,
    level: CompressionLevel | None = None,
) -> CompressionResult:
    """Convenience wrapper around the compression plugin."""

    context = ConversionContext(
        input_path=input,
        output_path=output,
        config={"level": level},
    )
    tool = registry.create("compress", context)
    return tool.run()


def convert_document(
    input: str | Path | pdf2docx.PdfDocument,
    output: str | Path | None = None,
    *,
    options: ConversionOptions | None = None,
    metadata: ConversionMetadata | None = None,
) -> ConversionResult:
    """Convenience wrapper for PDF → DOCX conversion using the plugin system."""

    if isinstance(input, (str, Path)):
        return convert_pdf_to_docx(input, output, options=options, metadata=metadata)

    config = {"options": options, "metadata": metadata}
    context = ConversionContext(output_path=output, config={"document": input, **config})
    tool = registry.create("convert_docx", context)
    return tool.run()


def protect_document(
    input: str | Path,
    output: str | Path,
    password: str,
    *,
    owner_password: str | None = None,
) -> Path:
    """Convenience wrapper around the encrypt plugin."""

    context = ConversionContext(
        input_path=input,
        output_path=output,
        config={"password": password, "owner_password": owner_password},
    )
    tool = registry.create("encrypt", context)
    return tool.run()


def unprotect_document(input: str | Path, output: str | Path, password: str) -> Path:
    """Convenience wrapper around the decrypt plugin."""

    context = ConversionContext(
        input_path=input,
        output_path=output,
        config={"password": password},
    )
    tool = registry.create("decrypt", context)
    return tool.run()


def is_document_encrypted(path: str | Path) -> bool:
    """Convenience wrapper around :func:`security.is_pdf_encrypted`."""

    return is_pdf_encrypted(path)
