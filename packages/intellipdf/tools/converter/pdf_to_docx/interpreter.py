"""Bridge that executes the PdfToDocx conversion pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ....pdf2docx.converter import (
    ConversionMetadata,
    ConversionOptions,
    ConversionResult,
    PdfToDocxConverter,
)


class DocxInterpreter:
    """Wrapper around :class:`PdfToDocxConverter` simplifying configuration."""

    def __init__(self, options: ConversionOptions | None = None) -> None:
        self.converter = PdfToDocxConverter(options)

    def run(
        self,
        input_document: Any,
        output_path: str | Path | None,
        *,
        metadata: ConversionMetadata | None = None,
    ) -> ConversionResult:
        return self.converter.convert(input_document, output_path, metadata=metadata)
