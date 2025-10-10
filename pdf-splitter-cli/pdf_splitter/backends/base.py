"""Backend protocol for PDF operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol


@dataclass
class BackendDocument:
    """Represents a loaded PDF document with backend-specific helpers."""

    num_pages: int
    file_size: int

    def iter_pages(self) -> Iterable[object]:
        raise NotImplementedError

    def get_page(self, index: int) -> object:
        raise NotImplementedError

    def copy_metadata(
        self,
        writer: object,
        *,
        title_suffix: str = "",
        pages_label: str | None = None,
    ) -> None:
        raise NotImplementedError


class PDFBackend(Protocol):
    """Protocol defining backend operations for PDF reading/writing."""

    def load(self, pdf_path: str, password: str | None = None) -> BackendDocument:
        """Load a PDF file and return a backend document wrapper."""

    def new_writer(self) -> object:
        """Return a backend writer instance."""

    def write(self, writer: object, destination: str) -> None:
        """Persist a writer to the destination path."""
