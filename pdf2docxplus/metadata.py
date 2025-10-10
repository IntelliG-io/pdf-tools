"""Metadata extraction and application utilities."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Mapping, MutableMapping, Optional

from docx import Document
from pypdf import PdfReader

from .exceptions import MetadataError
from .utils import parse_pdf_date, to_path

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class PDFMetadata:
    """Structured representation of PDF document metadata."""

    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    keywords: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[datetime] = None
    modification_date: Optional[datetime] = None
    additional_properties: Mapping[str, str] | None = None


def _normalise_metadata(raw: MutableMapping[str, str]) -> Dict[str, str]:
    cleaned: Dict[str, str] = {}
    for key, value in raw.items():
        if not value:
            continue
        normalized_key = key[1:] if key.startswith("/") else key
        cleaned[normalized_key] = str(value)
    return cleaned


def extract_metadata(input_path: str | Path) -> PDFMetadata:
    """Extract metadata from a PDF document."""
    path = to_path(input_path)
    LOGGER.info("Extracting metadata from %s", path)
    try:
        reader = PdfReader(str(path))
    except Exception as exc:  # pragma: no cover - library exception types vary
        raise MetadataError(f"Unable to open PDF for metadata extraction: {path}") from exc

    raw = reader.metadata or {}
    normalized = _normalise_metadata(raw)
    return PDFMetadata(
        title=normalized.get("Title"),
        author=normalized.get("Author"),
        subject=normalized.get("Subject"),
        keywords=normalized.get("Keywords"),
        creator=normalized.get("Creator"),
        producer=normalized.get("Producer"),
        creation_date=parse_pdf_date(normalized.get("CreationDate")),
        modification_date=parse_pdf_date(normalized.get("ModDate")),
        additional_properties={
            key: value
            for key, value in normalized.items()
            if key
            not in {
                "Title",
                "Author",
                "Subject",
                "Keywords",
                "Creator",
                "Producer",
                "CreationDate",
                "ModDate",
            }
        }
        or None,
    )


def apply_metadata_to_docx(docx_path: str | Path, metadata: PDFMetadata) -> None:
    """Apply extracted PDF metadata to a DOCX document."""
    path = to_path(docx_path)
    LOGGER.info("Applying metadata to %s", path)
    try:
        document = Document(str(path))
    except Exception as exc:  # pragma: no cover
        raise MetadataError(f"Unable to open DOCX document: {path}") from exc

    core = document.core_properties
    if metadata.title:
        core.title = metadata.title
    if metadata.author:
        core.author = metadata.author
    if metadata.subject:
        core.subject = metadata.subject
    if metadata.keywords:
        core.keywords = metadata.keywords
    if metadata.creation_date:
        core.created = metadata.creation_date.astimezone(timezone.utc)
    if metadata.modification_date:
        core.modified = metadata.modification_date.astimezone(timezone.utc)

    if metadata.additional_properties:
        custom = getattr(document, "custom_properties", None)
        if custom is None:
            LOGGER.warning("python-docx installation does not support custom properties; skipping")
        else:
            for key, value in metadata.additional_properties.items():
                try:
                    custom[key] = value
                except AttributeError:
                    if custom.exists(key):
                        custom.remove(key)
                    custom.add(key, value)

    document.save(str(path))
