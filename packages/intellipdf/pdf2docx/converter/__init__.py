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

        if _is_pdf_document_like(input_document):
            document = input_document  # type: ignore[assignment]
            page_count = document.page_count
            page_numbers = self._resolve_page_numbers(page_count, self.options.page_numbers)
            tagged = getattr(document, "tagged", False)
            metadata_map = getattr(document, "metadata", None)
            base_metadata = _metadata_from_mapping(metadata_map)
            builder = _DocumentBuilder(
                base_metadata,
                strip_whitespace=self.options.strip_whitespace,
                include_outline_toc=self.options.include_outline_toc,
                generate_toc_field=self.options.generate_toc_field,
                footnotes_as_endnotes=self.options.footnotes_as_endnotes,
            )
            builder.register_outline(getattr(document, "outline", None))
            selected = set(page_numbers)
            order = {page_number: position for position, page_number in enumerate(page_numbers)}
            sorted_pages: list[tuple[int, Page]] = []
            for index, page in enumerate(document.iter_pages()):
                if index in selected:
                    sorted_pages.append((order.get(index, index), page))
            for _, page in sorted(sorted_pages, key=lambda item: item[0]):
                builder.process_page(page, page.number)  # type: ignore[arg-type]
            document_ir = builder.build(tagged=tagged, page_count=len(page_numbers))
        else:
            source_path = Path(input_document)
            reader = PdfReader(str(source_path))
            page_count = len(reader.pages)
            page_numbers = self._resolve_page_numbers(page_count, self.options.page_numbers)
            struct_roles, global_roles, tagged = extract_struct_roles(reader)
            base_metadata = _metadata_from_mapping(reader.metadata)
            builder = _DocumentBuilder(
                base_metadata,
                strip_whitespace=self.options.strip_whitespace,
                include_outline_toc=self.options.include_outline_toc,
                generate_toc_field=self.options.generate_toc_field,
                footnotes_as_endnotes=self.options.footnotes_as_endnotes,
            )
            builder.register_outline(extract_outline(reader))
            global_iter = iter(global_roles)
            for index in page_numbers:
                page = reader.pages[index]
                roles_iter = _chain_roles(struct_roles.get(index, []), global_iter)
                page_primitives = page_from_reader(
                    page,
                    roles_iter,
                    index,
                    strip_whitespace=self.options.strip_whitespace,
                    reader=reader,
                )
                builder.process_page(page_primitives, index)
            document_ir = builder.build(tagged=tagged, page_count=len(page_numbers))

        document_ir.metadata = _merge_metadata(document_ir.metadata, metadata)
        stats = write_docx(document_ir, destination)
        return ConversionResult(
            output_path=destination.resolve(),
            page_count=stats.pages,
            paragraph_count=stats.paragraphs,
            word_count=stats.words,
            line_count=stats.lines,
            tagged_pdf=document_ir.tagged_pdf,
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
