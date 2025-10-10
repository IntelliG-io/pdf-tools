"""Splitting and extraction utilities for :mod:`intellipdf`."""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Iterable, List, Sequence

from pypdf import PdfReader, PdfWriter

from .exceptions import InvalidPageRangeError, PDFSplitXError
from .optimizers import optimize_pdf
from .utils import PageRange, build_output_filename, coerce_path, normalize_pages, parse_page_ranges
from .validators import validate_pdf

LOGGER = logging.getLogger("intellipdf.split")
_OPTIMIZE_ENV_VARS = ("INTELLIPDF_SPLIT_OPTIMIZE", "PDFSPLITX_OPTIMIZE")


def _should_optimize() -> bool:
    for env_name in _OPTIMIZE_ENV_VARS:
        value = os.getenv(env_name)
        if value is not None:
            return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _write_document(writer: PdfWriter, destination: Path, metadata: dict | None) -> None:
    if metadata:
        writer.add_metadata(metadata)
    with destination.open("wb") as output_stream:
        writer.write(output_stream)

    if _should_optimize():
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            temp_path = Path(tmp_file.name)
        shutil.copyfile(destination, temp_path)
        if optimize_pdf(temp_path, destination):
            LOGGER.info("Optimised PDF written to %s", destination)
        try:
            temp_path.unlink(missing_ok=True)
        except AttributeError:  # pragma: no cover - Python <3.8 compatibility fallback
            if temp_path.exists():
                temp_path.unlink()


def split_pdf(
    input: str | Path,
    output_dir: str | Path,
    *,
    mode: str = "range",
    ranges: str | Sequence[object] | None = None,
    pages: Sequence[int | str] | None = None,
) -> List[Path]:
    """Split a PDF document according to the requested mode.

    Args:
        input: Source PDF file.
        output_dir: Directory in which to write generated files.
        mode: Either ``"range"`` (default) or ``"pages"``.
        ranges: Range specification used when ``mode="range"``.
        pages: Explicit page numbers used when ``mode="pages"``.

    Returns:
        A list of paths to the generated PDF files.
    """

    input_path = coerce_path(input)
    output_path = coerce_path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    validate_pdf(input_path)
    reader = PdfReader(str(input_path))
    total_pages = len(reader.pages)
    metadata = dict(reader.metadata or {})
    base_name = input_path.stem

    generated_files: List[Path] = []

    if mode == "range":
        page_ranges = parse_page_ranges(ranges, total_pages=total_pages)
        for page_range in page_ranges:
            writer = PdfWriter()
            for page_num in range(page_range.start, page_range.end + 1):
                writer.add_page(reader.pages[page_num - 1])
            destination = output_path / build_output_filename(base_name, page_range)
            LOGGER.info(
                "Writing pages %s-%s to %s", page_range.start, page_range.end, destination
            )
            _write_document(writer, destination, metadata)
            generated_files.append(destination)
    elif mode == "pages":
        if pages is None:
            raise InvalidPageRangeError([pages])
        page_numbers = normalize_pages(pages, total_pages=total_pages)
        for page_number in page_numbers:
            writer = PdfWriter()
            writer.add_page(reader.pages[page_number - 1])
            destination = output_path / build_output_filename(base_name, page_number)
            LOGGER.info("Writing page %s to %s", page_number, destination)
            _write_document(writer, destination, metadata)
            generated_files.append(destination)
    else:
        raise PDFSplitXError(f"Unsupported split mode: {mode}")

    return generated_files


def extract_pages(
    input: str | Path,
    page_numbers: Sequence[int | str],
    output: str | Path,
) -> Path:
    """Extract ``page_numbers`` from ``input`` into a new PDF at ``output``."""

    input_path = coerce_path(input)
    output_path = coerce_path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    validate_pdf(input_path)
    reader = PdfReader(str(input_path))
    total_pages = len(reader.pages)
    metadata = dict(reader.metadata or {})

    pages = normalize_pages(page_numbers, total_pages=total_pages)

    writer = PdfWriter()
    for page_number in pages:
        writer.add_page(reader.pages[page_number - 1])

    LOGGER.info("Extracting pages %s to %s", pages, output_path)
    _write_document(writer, output_path, metadata)

    return output_path
