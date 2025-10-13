"""Shared PDF parsing helpers for IntelliPDF tools."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from pypdf import PdfReader

from .utils import resolve_path


class PDFParser:
    """Lightweight wrapper around :class:`pypdf.PdfReader` with caching support."""

    def __init__(self, source: str | Path, *, preload: bool = False) -> None:
        self.source = resolve_path(source)
        self._reader: PdfReader | None = None
        if preload:
            self.load()

    @property
    def reader(self) -> PdfReader:
        """Return a cached :class:`PdfReader` instance for ``source``."""

        return self.load()

    def load(self) -> PdfReader:
        if self._reader is None:
            self._reader = PdfReader(str(self.source))
        return self._reader

    def metadata(self) -> dict[str, str]:
        reader = self.reader
        return {key: str(value) for key, value in (reader.metadata or {}).items()}

    def page_count(self) -> int:
        return len(self.reader.pages)

    def iter_pages(self, *, indices: Optional[Iterable[int]] = None):
        reader = self.reader
        if indices is None:
            yield from reader.pages
            return
        for index in indices:
            yield reader.pages[index]
