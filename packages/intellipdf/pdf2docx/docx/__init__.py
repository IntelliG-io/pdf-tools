"""DOCX writing utilities."""

from __future__ import annotations

from .writer import write_docx
from .types import CoreProperties, DocumentStatistics

__all__ = ["write_docx", "CoreProperties", "DocumentStatistics"]
