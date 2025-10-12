"""Dataclasses used by the DOCX writer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .namespaces import DEFAULT_TIMESTAMP

__all__ = ["CoreProperties", "DocumentStatistics"]


@dataclass(slots=True)
class CoreProperties:
    """Metadata for the DOCX core properties part."""

    title: str | None = None
    creator: str | None = None
    description: str | None = None
    subject: str | None = None
    keywords: str | None = None
    last_modified_by: str | None = None
    created: datetime = DEFAULT_TIMESTAMP
    modified: datetime | None = None
    language: str | None = None
    revision: str | None = None

    def normalise(self) -> "CoreProperties":
        if self.created is None:
            self.created = DEFAULT_TIMESTAMP
        if self.modified is None:
            self.modified = self.created
        if self.revision is None:
            self.revision = "1"
        if self.last_modified_by is None:
            self.last_modified_by = self.creator
        return self


@dataclass(slots=True)
class DocumentStatistics:
    """Aggregated statistics required for docProps/app.xml."""

    pages: int = 0
    paragraphs: int = 0
    words: int = 0
    lines: int = 0
    characters: int = 0
    characters_with_spaces: int = 0

    def update_from_paragraph(self, text: str) -> None:
        self.paragraphs += 1
        self.characters_with_spaces += len(text)
        stripped = text.strip()
        if stripped:
            self.words += len(stripped.split())
            self.characters += len(stripped)
            self.lines += stripped.count("\n") + 1

    def update_from_document(self, page_count: int) -> None:
        self.pages = page_count
