"""Validation helpers for :mod:`intellipdf.compress`."""

from __future__ import annotations

import logging
from pathlib import Path

from pypdf import PdfReader

from .exceptions import InvalidPDFError
from .optimizers import BackendType, detect_backend
from .utils import resolve_path, run_subprocess

_LOGGER = logging.getLogger("intellipdf.compress")


def validate_pdf(path: str | Path, *, use_external: bool = True) -> None:
    """Validate the PDF at *path*.

    This method first performs a structural parse using :mod:`pypdf`. When
    ``use_external`` is set and ``qpdf`` is available, a ``qpdf --check`` run is
    performed to catch additional structural issues.
    """

    pdf_path = resolve_path(path)
    _LOGGER.debug("Validating PDF at %s", pdf_path)

    try:
        reader = PdfReader(str(pdf_path))
        if len(reader.pages) == 0:
            raise InvalidPDFError("PDF contains no pages")
    except Exception as exc:  # pragma: no cover - exercised via tests
        raise InvalidPDFError(f"Failed to parse PDF: {exc}") from exc

    if use_external:
        backend = detect_backend(preferred=(BackendType.QPDF,))
        if backend and backend.type is BackendType.QPDF:
            _LOGGER.debug("Running qpdf --check on %s", pdf_path)
            run_subprocess([backend.executable, "--check", str(pdf_path)], check=True)


__all__ = ["validate_pdf"]
