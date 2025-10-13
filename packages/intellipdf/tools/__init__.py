"""Namespace for pluggable IntelliPDF tools."""

from __future__ import annotations

from .common.pipeline import registry


def load_builtin_plugins() -> None:
    from .splitter import split  # noqa: F401  # register split and extract tools
    from .merger import merge  # noqa: F401
    from .compressor import compress  # noqa: F401
    from .encryptor import encrypt  # noqa: F401
    from .converter.pdf_to_docx import exporter  # noqa: F401


__all__ = ["registry", "load_builtin_plugins"]
