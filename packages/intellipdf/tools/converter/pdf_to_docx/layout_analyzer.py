"""Layout analysis utilities that build the converter intermediate representation."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean
from typing import Iterable, Iterator, Sequence

from intellipdf.core.parser import ParsedDocument

from .converter.builder import DocumentBuilder
from .converter.metadata import metadata_from_mapping
from .converter.reader import extract_outline, extract_struct_roles
from .converter.text import CapturedText, text_fragments_to_blocks
from .converter.types import ConversionOptions
from .interpreter import (
    Glyph,
    LineSegment,
    PageContent,
    PageImage,
    PDFContentInterpreter,
    VectorPath,
)
from .ir import Document, DocumentMetadata
from .primitives import (
    Image as PrimitiveImage,
    Line as PrimitiveLine,
    Page as PrimitivePage,
    Path as PrimitivePath,
)

__all__ = ["IntermediateRepresentation", "LayoutAnalyzer"]


@dataclass(slots=True)
class IntermediateRepresentation:
    """Container holding the analysed layout and semantic structure."""

    document: Document
    pages: Sequence[PrimitivePage]
    page_contents: Sequence[PageContent]
    metadata: DocumentMetadata
    tagged_pdf: bool


class LayoutAnalyzer:
    """Convert low level glyphs, images, and vector paths into IR structures."""

    def __init__(self, options: ConversionOptions | None = None) -> None:
        self.options = options or ConversionOptions()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def analyse(
        self,
        parsed: ParsedDocument,
        *,
        contents: Sequence[PageContent] | None = None,
    ) -> IntermediateRepresentation:
        interpreter = PDFContentInterpreter(parsed)
        reader = parsed.resolver.reader

        page_numbers = self._resolve_page_numbers(len(parsed.pages), self.options.page_numbers)
        provided = {content.page_number: content for content in contents or ()}
        selected_contents: list[PageContent] = []
        for page_index in page_numbers:
            content = provided.get(page_index)
            if content is None:
                content = interpreter.interpret_page(page_index)
            selected_contents.append(content)

        struct_roles, global_roles, tagged_pdf = self._safe_extract_struct_roles(reader)
        global_iter: Iterator[str] = iter(global_roles)

        pages: list[PrimitivePage] = []
        for content in selected_contents:
            roles = list(self._chain_roles(struct_roles.get(content.page_number, []), global_iter))
            blocks = self._build_text_blocks(content, roles)
            images = [self._to_primitive_image(image) for image in content.images]
            lines = [self._to_primitive_line(line) for line in content.lines]
            paths = [self._to_primitive_path(path) for path in content.paths]
            page = PrimitivePage(
                number=content.page_number,
                width=content.width,
                height=content.height,
                text_blocks=blocks,
                images=images,
                lines=lines,
                paths=paths,
                tagged_roles=roles,
            )
            pages.append(page)

        metadata = metadata_from_mapping(parsed.metadata)
        builder = DocumentBuilder(
            metadata,
            strip_whitespace=self.options.strip_whitespace,
            include_outline_toc=self.options.include_outline_toc,
            generate_toc_field=self.options.generate_toc_field,
            footnotes_as_endnotes=self.options.footnotes_as_endnotes,
        )
        outline = self._safe_extract_outline(reader)
        builder.register_outline(outline)
        for page in sorted(pages, key=lambda item: item.number):
            builder.process_page(page, page.number)
        document = builder.build(tagged=tagged_pdf, page_count=len(page_numbers))
        return IntermediateRepresentation(
            document=document,
            pages=tuple(pages),
            page_contents=tuple(selected_contents),
            metadata=document.metadata,
            tagged_pdf=tagged_pdf,
        )

    # ------------------------------------------------------------------ #
    # Glyph clustering helpers
    # ------------------------------------------------------------------ #
    def _build_text_blocks(self, content: PageContent, roles: Sequence[str]) -> list:
        fragments = list(self._glyphs_to_fragments(content.glyphs))
        fragments.extend(self._glyph_to_fragment(glyph) for glyph in content.glyphs if glyph.vertical)
        return text_fragments_to_blocks(
            fragments,
            page_width=content.width,
            page_height=content.height,
            roles=list(roles),
            strip_whitespace=self.options.strip_whitespace,
        )

    def _glyphs_to_fragments(self, glyphs: Sequence[Glyph]) -> Iterable[CapturedText]:
        horizontal = [glyph for glyph in glyphs if not glyph.vertical]
        for line in self._cluster_lines(horizontal):
            for group in self._cluster_words(line):
                yield self._word_to_fragment(group)

    def _cluster_lines(self, glyphs: Sequence[Glyph]) -> list[list[Glyph]]:
        lines: list[list[Glyph]] = []
        for glyph in sorted(glyphs, key=lambda item: (-item.y, item.x)):
            placed = False
            for line in lines:
                baseline = fmean(item.y for item in line)
                tolerance = max(self._font_size(glyph), fmean(self._font_size(item) for item in line)) * 0.6
                if abs(glyph.y - baseline) <= tolerance:
                    line.append(glyph)
                    placed = True
                    break
            if not placed:
                lines.append([glyph])
        return lines

    def _cluster_words(self, line: Sequence[Glyph]) -> list[list[Glyph]]:
        if not line:
            return []
        words: list[list[Glyph]] = []
        current: list[Glyph] = []
        previous_end = float("-inf")
        for glyph in sorted(line, key=lambda item: item.x):
            start = glyph.x
            width = self._glyph_width(glyph)
            if current:
                gap = start - previous_end
                threshold = max(self._font_size(glyph), self._font_size(current[-1])) * 0.55
                if gap > threshold:
                    words.append(current)
                    current = []
            current.append(glyph)
            previous_end = start + width
        if current:
            words.append(current)
        return words

    def _word_to_fragment(self, glyphs: Sequence[Glyph]) -> CapturedText:
        text = "".join(glyph.text for glyph in glyphs)
        x = min(glyph.x for glyph in glyphs)
        y = fmean(glyph.y for glyph in glyphs)
        font_name = next((glyph.font_name for glyph in glyphs if glyph.font_name), None)
        font_size = fmean(self._font_size(glyph) for glyph in glyphs)
        color = next((glyph.color for glyph in glyphs if glyph.color), None)
        vertical = any(glyph.vertical for glyph in glyphs)
        return CapturedText(
            text=text,
            x=float(x),
            y=float(y),
            font_name=font_name,
            font_size=float(font_size) if font_size else None,
            vertical=vertical,
            color=color,
        )

    def _glyph_to_fragment(self, glyph: Glyph) -> CapturedText:
        return CapturedText(
            text=glyph.text,
            x=float(glyph.x),
            y=float(glyph.y),
            font_name=glyph.font_name,
            font_size=glyph.font_size,
            vertical=glyph.vertical,
            color=glyph.color,
        )

    @staticmethod
    def _font_size(glyph: Glyph) -> float:
        return float(glyph.font_size or 12.0)

    def _glyph_width(self, glyph: Glyph) -> float:
        return max(len(glyph.text), 1) * self._font_size(glyph) * 0.5

    # ------------------------------------------------------------------ #
    # Primitive conversions
    # ------------------------------------------------------------------ #
    @staticmethod
    def _to_primitive_image(image: PageImage) -> PrimitiveImage:
        return PrimitiveImage(
            data=image.data,
            bbox=image.bbox,
            mime_type=image.mime_type,
            name=image.name,
        )

    @staticmethod
    def _to_primitive_line(line: LineSegment) -> PrimitiveLine:
        return PrimitiveLine(
            start=(float(line.start[0]), float(line.start[1])),
            end=(float(line.end[0]), float(line.end[1])),
            stroke_width=line.stroke_width,
        )

    @staticmethod
    def _to_primitive_path(path: VectorPath) -> PrimitivePath:
        return PrimitivePath(
            subpaths=[
                [(float(x), float(y)) for x, y in subpath]
                for subpath in path.subpaths
            ],
            stroke_color=path.stroke_color,
            fill_color=path.fill_color,
            stroke_width=path.stroke_width,
            fill_rule=path.fill_rule,
            stroke_alpha=path.stroke_alpha,
            fill_alpha=path.fill_alpha,
            is_rectangle=path.is_rectangle,
        )

    # ------------------------------------------------------------------ #
    # Metadata / outline helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _safe_extract_struct_roles(reader) -> tuple[dict[int, list[str]], list[str], bool]:
        try:
            return extract_struct_roles(reader)
        except Exception:
            return {}, [], False

    @staticmethod
    def _safe_extract_outline(reader):
        try:
            return extract_outline(reader)
        except Exception:
            return None

    @staticmethod
    def _chain_roles(page_roles: Sequence[str], global_iter: Iterator[str]) -> Iterable[str]:
        for role in page_roles:
            yield role
        yield from global_iter

    @staticmethod
    def _resolve_page_numbers(total_pages: int, requested: Sequence[int] | None) -> list[int]:
        if requested is None:
            return list(range(total_pages))
        result: list[int] = []
        for index in requested:
            if index < 0 or index >= total_pages:
                raise IndexError(f"Page index {index} out of bounds for document with {total_pages} pages")
            result.append(index)
        return result
