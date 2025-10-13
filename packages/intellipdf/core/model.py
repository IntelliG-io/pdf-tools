"""Shared domain models used across IntelliPDF tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


@dataclass(slots=True)
class DocumentMetadata:
    title: str | None = None
    author: str | None = None
    producer: str | None = None
    creation_date: str | None = None
    modified_date: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PDFDocument:
    path: Path
    page_count: int
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)


@dataclass(slots=True)
class ToolResult:
    """Normalized result object shared by CLI and API wrappers."""

    output: Path | None
    artifacts: Iterable[Path] = field(default_factory=tuple)
    details: dict[str, Any] = field(default_factory=dict)
