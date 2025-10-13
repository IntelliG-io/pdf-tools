"""Wrapper around the DOCX writer utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .docx import write_docx


class DocxWriter:
    def write(self, document: Any, destination: str | Path, *, metadata: dict | None = None) -> Path:
        write_docx(document, destination, metadata=metadata)
        return Path(destination).resolve()
