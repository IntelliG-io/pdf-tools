"""Metadata helpers for PDF to DOCX conversion."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Mapping

from ..ir import DocumentMetadata
from .constants import PDF_DATE_PREFIX
from .types import ConversionMetadata

__all__ = [
    "metadata_from_mapping",
    "merge_metadata",
    "parse_pdf_date",
]


def metadata_from_mapping(metadata: Mapping[str, object] | None) -> DocumentMetadata:
    result = DocumentMetadata()
    if not metadata:
        return result

    def _get(key: str) -> str | None:
        value = metadata.get(key)
        if value is None:
            return None
        return str(value)

    title = _get("/Title") or _get("Title")
    author = _get("/Author") or _get("Author")
    subject = _get("/Subject") or _get("Subject")
    description = _get("/Description") or _get("Description")
    keywords = _get("/Keywords") or _get("Keywords")
    language = _get("/Lang") or _get("Lang")
    revision = _get("/Revision") or _get("Revision")
    last_modified_by = _get("/LastModifiedBy") or _get("LastModifiedBy")
    created_raw = _get("/CreationDate") or _get("CreationDate")
    modified_raw = _get("/ModDate") or _get("ModDate")

    if title:
        result.title = title
    if author:
        result.author = author
    if subject:
        result.subject = subject
    if description:
        result.description = description
    if keywords:
        result.keywords = [item.strip() for item in keywords.split(",") if item.strip()]
    if created_raw:
        parsed = parse_pdf_date(created_raw)
        if parsed:
            result.created = parsed
    if modified_raw:
        parsed = parse_pdf_date(modified_raw)
        if parsed:
            result.modified = parsed
    if language:
        result.language = language
    if revision:
        result.revision = revision
    if last_modified_by:
        result.last_modified_by = last_modified_by
    return result


def merge_metadata(base: DocumentMetadata, override: ConversionMetadata | None) -> DocumentMetadata:
    if override is None:
        return base
    return DocumentMetadata(
        title=override.title if override.title is not None else base.title,
        author=override.author if override.author is not None else base.author,
        subject=override.subject if override.subject is not None else base.subject,
        description=override.description if override.description is not None else base.description,
        keywords=list(override.keywords) if override.keywords is not None else list(base.keywords),
        created=override.created if override.created is not None else base.created,
        modified=override.modified if override.modified is not None else base.modified,
        language=override.language if override.language is not None else base.language,
        revision=override.revision if override.revision is not None else base.revision,
        last_modified_by=
            override.last_modified_by if override.last_modified_by is not None else base.last_modified_by,
    )


def parse_pdf_date(value: str) -> datetime | None:
    text = value.strip()
    if text.startswith(PDF_DATE_PREFIX):
        text = text[len(PDF_DATE_PREFIX) :]
    try:
        year = int(text[0:4])
        month = int(text[4:6]) if len(text) >= 6 else 1
        day = int(text[6:8]) if len(text) >= 8 else 1
        hour = int(text[8:10]) if len(text) >= 10 else 0
        minute = int(text[10:12]) if len(text) >= 12 else 0
        second = int(text[12:14]) if len(text) >= 14 else 0
    except ValueError:
        return None
    tz = timezone.utc
    if len(text) > 14:
        sign = text[14]
        if sign in "+-" and len(text) >= 19:
            try:
                offset_hours = int(text[15:17])
                offset_minutes = int(text[18:20]) if len(text) >= 20 else 0
            except ValueError:
                offset_hours = 0
                offset_minutes = 0
            delta = timedelta(hours=offset_hours, minutes=offset_minutes)
            if sign == "-":
                delta = -delta
            tz = timezone(delta)
    try:
        return datetime(year, month, day, hour, minute, second, tzinfo=tz)
    except ValueError:
        return None
