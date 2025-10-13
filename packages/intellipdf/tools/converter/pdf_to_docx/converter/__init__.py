"""High level PDF → DOCX conversion pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

from pypdf import PdfReader

from ..docx import write_docx
from ..primitives import Page
from .builder import DocumentBuilder as _DocumentBuilder
from .fonts import apply_translation_map as _apply_translation_map, font_translation_maps as _font_translation_maps
from .layout import blocks_to_paragraphs_static as _blocks_to_paragraphs_static
from .lists import normalise_text_for_numbering as _normalise_text_for_numbering
from .metadata import merge_metadata as _merge_metadata, metadata_from_mapping as _metadata_from_mapping, parse_pdf_date as _parse_pdf_date
from .pipeline import PdfToDocxPipeline
from .reader import extract_outline, extract_struct_roles, page_from_reader
from .text import CapturedText as _CapturedText
from .types import ConversionMetadata, ConversionOptions, ConversionResult, PdfDocumentLike

__all__ = [
    "ConversionMetadata",
    "ConversionOptions",
    "ConversionResult",
    "PdfDocumentLike",
    "PdfToDocxConverter",
    "convert_pdf_to_docx",
    "_CapturedText",
    "_DocumentBuilder",
    "_apply_translation_map",
    "_blocks_to_paragraphs_static",
    "_font_translation_maps",
    "_normalise_text_for_numbering",
    "_parse_pdf_date",
]


class PdfToDocxConverter:
    """High level PDF → DOCX conversion helper."""

    def __init__(self, options: ConversionOptions | None = None) -> None:
        self.options = options or ConversionOptions()

    def convert(
        self,
        input_document: str | Path | PdfDocumentLike,
        output_path: str | Path | None = None,
        *,
        metadata: ConversionMetadata | None = None,
    ) -> ConversionResult:
        destination = self._resolve_output_path(input_document, output_path)
        pipeline = PdfToDocxPipeline(self.options)
        document_ir, stats, log = pipeline.run(input_document, destination, metadata)
        pages, paragraphs, words, lines = stats
        return ConversionResult(
            output_path=destination.resolve(),
            page_count=pages,
            paragraph_count=paragraphs,
            word_count=words,
            line_count=lines,
            tagged_pdf=document_ir.tagged_pdf,
            log=log,
        )

    def _extract_struct_roles(self, reader: PdfReader):
        return extract_struct_roles(reader)

    def _resolve_page_numbers(
        self,
        total_pages: int,
        requested_pages: Sequence[int] | None,
    ) -> list[int]:
        if requested_pages is None:
            return list(range(total_pages))
        result: list[int] = []
        for page in requested_pages:
            if page < 0 or page >= total_pages:
                raise ValueError(f"Page index {page} out of bounds for document with {total_pages} pages")
            result.append(page)
        return result

    def _resolve_output_path(
        self,
        source: str | Path | PdfDocumentLike,
        destination: str | Path | None,
    ) -> Path:
        if destination is not None:
            return Path(destination)
        if isinstance(source, (str, Path)):
            return Path(source).with_suffix(".docx")
        raise ValueError("output_path must be provided when converting from PdfDocument objects")


def convert_pdf_to_docx(
    input_document: str | Path | PdfDocumentLike,
    output_path: str | Path | None = None,
    *,
    options: ConversionOptions | None = None,
    metadata: ConversionMetadata | None = None,
) -> ConversionResult:
    """Convenience wrapper around :class:`PdfToDocxConverter`."""

    converter = PdfToDocxConverter(options)
    return converter.convert(input_document, output_path, metadata=metadata)


def _is_pdf_document_like(value: object) -> bool:
    return isinstance(value, PdfDocumentLike)


def _chain_roles(page_roles: Sequence[str], global_roles: Iterable[str]) -> Iterable[str]:
    for role in page_roles:
        yield role
    yield from global_roles
