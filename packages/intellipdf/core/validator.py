"""Validation helpers shared by IntelliPDF tools."""

from __future__ import annotations

from pathlib import Path

from .utils import resolve_path


class ValidationError(RuntimeError):
    """Raised when a PDF file fails validation."""


def ensure_pdf_exists(path: str | Path) -> Path:
    resolved = resolve_path(path)
    if not resolved.exists():
        raise ValidationError(f"PDF file not found: {resolved}")
    if resolved.suffix.lower() != ".pdf":
        raise ValidationError(f"Expected a PDF file, got: {resolved}")
    return resolved


def ensure_output_parent(path: str | Path) -> Path:
    resolved = resolve_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved
