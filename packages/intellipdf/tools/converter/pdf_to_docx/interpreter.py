"""PDF content stream interpreter exposing structured page primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
import copy

from pypdf.generic import DictionaryObject

from intellipdf.core.parser import ParsedDocument, ParsedPage
from .converter.reader import (
    ContentStreamState,
    capture_text_fragments,
    extract_vector_graphics,
)
from .converter.images import extract_page_images
from .converter import ConversionMetadata, ConversionOptions, ConversionResult, PdfToDocxConverter
from .primitives import BoundingBox, Image as PrimitiveImage, Line as PrimitiveLine, Path as PrimitivePath

__all__ = [
    "Glyph",
    "LineSegment",
    "VectorPath",
    "PageImage",
    "PageContent",
    "PDFContentInterpreter",
    "DocxInterpreter",
]


# -- Structured primitives ---------------------------------------------------


@dataclass(slots=True)
class Glyph:
    """Single textual glyph extracted from a content stream."""

    text: str
    x: float
    y: float
    font_name: str | None = None
    font_size: float | None = None
    color: str | None = None
    vertical: bool = False


@dataclass(slots=True)
class LineSegment:
    """Straight vector segment rendered on the page."""

    start: tuple[float, float]
    end: tuple[float, float]
    stroke_width: float | None = None


@dataclass(slots=True)
class VectorPath:
    """Compound Bézier path with optional fill and stroke attributes."""

    subpaths: list[list[tuple[float, float]]]
    stroke_color: tuple[float, float, float] | None = None
    fill_color: tuple[float, float, float] | None = None
    stroke_width: float | None = None
    fill_rule: str = "nonzero"
    stroke_alpha: float = 1.0
    fill_alpha: float = 1.0
    is_rectangle: bool = False


@dataclass(slots=True)
class PageImage:
    """Raster image placement."""

    data: bytes
    bbox: BoundingBox
    mime_type: str | None = None
    name: str | None = None


@dataclass(slots=True)
class PageContent:
    """Structured result produced by :class:`PDFContentInterpreter`."""

    page_number: int
    width: float
    height: float
    glyphs: list[Glyph] = field(default_factory=list)
    images: list[PageImage] = field(default_factory=list)
    lines: list[LineSegment] = field(default_factory=list)
    paths: list[VectorPath] = field(default_factory=list)
    resources: dict[str, Any] | None = None


# -- Interpreter implementation ---------------------------------------------


class PDFContentInterpreter:
    """Decode PDF content streams into structured primitives."""

    def __init__(self, document: ParsedDocument) -> None:
        self.document = document
        self._reader = document.resolver.reader
        self._page_states: dict[int, ContentStreamState] = {}

    def interpret_page(self, page: ParsedPage | int) -> PageContent:
        """Interpret a :class:`ParsedPage` (or page index) into primitives."""

        parsed = self._lookup_page(page)
        geometry = parsed.geometry
        width, height = self._page_dimensions(geometry)
        content = PageContent(
            page_number=parsed.number,
            width=width,
            height=height,
            resources=self._clone_resources(parsed.resources),
        )

        page_obj = self._page_dictionary(parsed)
        if page_obj is None:
            return content

        state = self._initialise_page_state(parsed.number)
        fragments = capture_text_fragments(page_obj, self._reader, state=state)
        images = extract_page_images(page_obj, self._reader)
        lines, paths = extract_vector_graphics(page_obj, self._reader)

        content.glyphs.extend(self._build_glyphs(fragments, parsed))
        content.images.extend(self._build_images(images, parsed))
        content.lines.extend(self._build_lines(lines, parsed))
        content.paths.extend(self._build_paths(paths, parsed))
        return content

    # -- Internal helpers -------------------------------------------------

    def _lookup_page(self, page: ParsedPage | int) -> ParsedPage:
        if isinstance(page, ParsedPage):
            return page
        pages = self.document.pages
        if page < 0 or page >= len(pages):
            raise IndexError(f"Page index {page} out of range")
        return pages[page]

    def _page_dictionary(self, page: ParsedPage) -> DictionaryObject | None:
        try:
            return self._reader.pages[page.number]  # type: ignore[index]
        except Exception:
            return None

    def _initialise_page_state(self, page_number: int) -> ContentStreamState:
        state = ContentStreamState()
        state.reset()
        self._page_states[page_number] = state
        return state

    def snapshot_state(self, page_number: int) -> dict[str, Any] | None:
        state = self._page_states.get(page_number)
        if state is None:
            return None
        return state.snapshot(page_number=page_number)

    def default_state(self) -> ContentStreamState:
        state = ContentStreamState()
        state.reset()
        return state

    def _page_dimensions(self, geometry) -> tuple[float, float]:
        left, bottom, right, top = geometry.media_box
        unit = geometry.user_unit or 1.0
        width = (right - left) * unit
        height = (top - bottom) * unit
        rotate = (geometry.rotate or 0) % 360
        if rotate in {90, 270}:
            width, height = height, width
        return float(width), float(height)

    def _clone_resources(self, resources: Mapping[str, Any] | None) -> dict[str, Any] | None:
        if not resources:
            return None
        try:
            return copy.deepcopy(resources)
        except Exception:
            return dict(resources)

    def _normalise_point(self, x: float, y: float, page: ParsedPage) -> tuple[float, float]:
        geometry = page.geometry
        left, bottom, right, top = geometry.media_box
        unit = geometry.user_unit or 1.0
        rotate = (geometry.rotate or 0) % 360

        x0 = (x - left) * unit
        y0 = (y - bottom) * unit
        width = (right - left) * unit
        height = (top - bottom) * unit

        if rotate == 90:
            return height - y0, x0
        if rotate == 180:
            return width - x0, height - y0
        if rotate == 270:
            return y0, width - x0
        return x0, y0

    def _normalise_bbox(self, bbox: BoundingBox, page: ParsedPage) -> BoundingBox:
        points = [
            self._normalise_point(bbox.left, bbox.bottom, page),
            self._normalise_point(bbox.left, bbox.top, page),
            self._normalise_point(bbox.right, bbox.bottom, page),
            self._normalise_point(bbox.right, bbox.top, page),
        ]
        xs = [pt[0] for pt in points]
        ys = [pt[1] for pt in points]
        return BoundingBox(
            left=min(xs),
            bottom=min(ys),
            right=max(xs),
            top=max(ys),
        )

    def _build_glyphs(self, fragments, page: ParsedPage) -> Iterable[Glyph]:
        unit = page.geometry.user_unit or 1.0
        for fragment in fragments:
            x, y = self._normalise_point(fragment.x, fragment.y, page)
            font_size = fragment.font_size * unit if fragment.font_size is not None else None
            yield Glyph(
                text=fragment.text,
                x=float(x),
                y=float(y),
                font_name=fragment.font_name,
                font_size=float(font_size) if font_size is not None else None,
                color=fragment.color,
                vertical=fragment.vertical,
            )

    def _build_images(self, images: Sequence[PrimitiveImage], page: ParsedPage) -> Iterable[PageImage]:
        for image in images:
            bbox = self._normalise_bbox(image.bbox, page)
            yield PageImage(
                data=image.data,
                bbox=bbox,
                mime_type=image.mime_type,
                name=image.name,
            )

    def _build_lines(self, lines: Sequence[PrimitiveLine], page: ParsedPage) -> Iterable[LineSegment]:
        unit = page.geometry.user_unit or 1.0
        for line in lines:
            start = self._normalise_point(*line.start, page=page)
            end = self._normalise_point(*line.end, page=page)
            stroke_width = line.stroke_width * unit if line.stroke_width is not None else None
            yield LineSegment(
                start=(float(start[0]), float(start[1])),
                end=(float(end[0]), float(end[1])),
                stroke_width=float(stroke_width) if stroke_width is not None else None,
            )

    def _build_paths(self, paths: Sequence[PrimitivePath], page: ParsedPage) -> Iterable[VectorPath]:
        unit = page.geometry.user_unit or 1.0
        for path in paths:
            subpaths = [
                [self._normalise_point(x, y, page) for x, y in subpath]
                for subpath in path.subpaths
            ]
            stroke_width = path.stroke_width * unit if path.stroke_width is not None else None
            yield VectorPath(
                subpaths=[[ (float(px), float(py)) for px, py in sub ] for sub in subpaths],
                stroke_color=path.stroke_color,
                fill_color=path.fill_color,
                stroke_width=float(stroke_width) if stroke_width is not None else None,
                fill_rule=path.fill_rule,
                stroke_alpha=path.stroke_alpha,
                fill_alpha=path.fill_alpha,
                is_rectangle=path.is_rectangle,
            )


# -- Legacy bridge -----------------------------------------------------------


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
