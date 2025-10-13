"""Shared type definitions for the converter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Protocol, Sequence, runtime_checkable

from ..primitives import Page

__all__ = [
    "ConversionMetadata",
    "ConversionOptions",
    "ConversionResult",
    "PdfDocumentLike",
]


@dataclass(slots=True)
class ConversionOptions:
    """Options controlling how a PDF is converted to DOCX."""

    page_numbers: Sequence[int] | None = None
    strip_whitespace: bool = True
    stream_pages: bool = True
    include_outline_toc: bool = True
    generate_toc_field: bool = True
    footnotes_as_endnotes: bool = False


@dataclass(slots=True)
class ConversionMetadata:
    """Metadata applied to the generated DOCX file."""

    title: str | None = None
    author: str | None = None
    subject: str | None = None
    description: str | None = None
    keywords: Sequence[str] | None = None
    created: datetime | None = None
    modified: datetime | None = None
    language: str | None = None
    revision: str | None = None
    last_modified_by: str | None = None


@dataclass(slots=True)
class ConversionResult:
    """Information about the produced DOCX document."""

    output_path: Path
    page_count: int
    paragraph_count: int
    word_count: int
    line_count: int
    tagged_pdf: bool
    log: tuple[str, ...] = ()


@runtime_checkable
class PdfDocumentLike(Protocol):
    page_count: int
    tagged: bool

    def iter_pages(self) -> Iterable[Page]:
        ...
