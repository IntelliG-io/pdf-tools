"""Merge functionality for the :mod:`intellipdf.merge` package."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

from pypdf import PdfReader, PdfWriter

from .exceptions import PdfMergeError
from .utils import PathLike, ensure_iterable, ensure_path
from .validators import get_pdf_info, validate_pdf

LOGGER = logging.getLogger("intellipdf.merge")


def _load_reader(path: Path) -> PdfReader:
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        LOGGER.debug("Attempting to decrypt encrypted PDF %s", path)
        try:
            reader.decrypt("")
        except Exception as exc:  # pragma: no cover - decrypt errors vary
            LOGGER.error("Failed to decrypt PDF %s: %s", path, exc)
            raise PdfMergeError(
                f"Unable to decrypt encrypted PDF: {path}"
            ) from exc
    return reader


def merge_pdfs(
    inputs: Iterable[PathLike],
    output: PathLike,
    *,
    metadata: bool = True,
    document_info: Mapping[str, object] | None = None,
    bookmarks: Sequence[str] | None = None,
) -> Path:
    """Merge *inputs* into *output* and return the resulting path.

    Args:
        inputs: An iterable of file paths to merge. They must point to
            readable PDF files.
        output: The output file path that will contain the merged PDF.
        metadata: When ``True`` metadata from the first readable input
            file is copied into the merged document.

    Raises:
        PdfMergeError: If merging fails for any reason.
    """

    pdf_paths = ensure_iterable(inputs)
    if not pdf_paths:
        raise PdfMergeError("No input PDFs provided")

    output_path = ensure_path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    writer = PdfWriter()
    first_metadata: Optional[dict[str, str]] = None
    bookmark_targets: list[tuple[str, int]] = []

    for index, pdf_path in enumerate(pdf_paths):
        LOGGER.debug("Processing input PDF %s", pdf_path)
        try:
            validate_pdf(pdf_path)
        except Exception as exc:  # pragma: no cover
            raise PdfMergeError(f"Invalid PDF: {pdf_path}") from exc

        reader = _load_reader(pdf_path)
        start_page_index = len(writer.pages)
        for page_index, page in enumerate(reader.pages):
            LOGGER.debug("Adding page %s from %s", page_index, pdf_path)
            writer.add_page(page)

        if bookmarks:
            try:
                title = bookmarks[index]
            except IndexError:
                title = None

            if not title:
                title = pdf_path.stem or f"Document {index + 1}"
            bookmark_targets.append((title, start_page_index))

        if metadata and first_metadata is None:
            try:
                info = get_pdf_info(pdf_path)
                first_metadata = {
                    key: str(value)
                    for key, value in info.metadata.items()
                    if isinstance(key, str) and value is not None
                }
            except PdfMergeError:
                raise
            except Exception as exc:  # pragma: no cover
                LOGGER.warning(
                    "Failed to capture metadata from %s: %s", pdf_path, exc
                )

    metadata_to_apply: dict[str, str] | None = None
    if document_info:
        metadata_to_apply = {}
        metadata_key_map = {
            "title": "/Title",
            "author": "/Author",
            "subject": "/Subject",
            "keywords": "/Keywords",
        }
        for key, value in document_info.items():
            if value is None:
                continue
            string_value = str(value).strip()
            if not string_value:
                continue
            pdf_key = metadata_key_map.get(key.lower(), None)
            if pdf_key is None:
                pdf_key = key if str(key).startswith("/") else f"/{key}"
            metadata_to_apply[pdf_key] = string_value
    elif metadata and first_metadata:
        metadata_to_apply = first_metadata

    if metadata_to_apply:
        LOGGER.debug("Setting metadata on merged PDF: %s", metadata_to_apply)
        writer.add_metadata(metadata_to_apply)

    if bookmark_targets:
        LOGGER.debug("Adding %d bookmark(s) to merged PDF", len(bookmark_targets))
        for title, page_index in bookmark_targets:
            try:
                writer.add_outline_item(title, writer.pages[page_index])
            except Exception as exc:  # pragma: no cover - defensive
                LOGGER.warning("Failed to add bookmark '%s': %s", title, exc)

    try:
        with output_path.open("wb") as output_handle:
            writer.write(output_handle)
    except Exception as exc:  # pragma: no cover - IO errors vary
        LOGGER.error("Failed to write merged PDF to %s: %s", output_path, exc)
        raise PdfMergeError(
            f"Failed to write merged PDF to {output_path}"
        ) from exc

    LOGGER.info("Merged %d PDFs into %s", len(pdf_paths), output_path)
    return output_path


__all__ = ["merge_pdfs"]
