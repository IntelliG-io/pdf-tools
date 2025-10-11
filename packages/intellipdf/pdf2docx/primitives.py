"""Common primitives shared between IntelliPDF and the PDF→DOCX converter."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Mapping, Sequence


@dataclass(slots=True)
class BoundingBox:
    """Axis-aligned rectangle using PDF coordinates."""

    left: float
    bottom: float
    right: float
    top: float

    def width(self) -> float:
        return max(0.0, self.right - self.left)

    def height(self) -> float:
        return max(0.0, self.top - self.bottom)


@dataclass(slots=True)
class TextBlock:
    """Text fragment extracted from a PDF page."""

    text: str
    bbox: BoundingBox
    font_name: str | None = None
    font_size: float | None = None
    role: str | None = None
    color: str | None = None
    bold: bool = False
    italic: bool = False
    underline: bool = False
    rtl: bool = False
    language: str | None = None
    superscript: bool = False
    subscript: bool = False
    vertical: bool = False
    background_color: str | None = None
    opacity: float | None = None


@dataclass(slots=True)
class Image:
    """Raster image embedded inside a page."""

    data: bytes
    bbox: BoundingBox
    mime_type: str | None = None
    name: str | None = None


@dataclass(slots=True)
class Line:
    """Straight line primitive used for table borders or separators."""

    start: tuple[float, float]
    end: tuple[float, float]
    stroke_width: float | None = None


@dataclass(slots=True)
class Path:
    """Vector path made up of one or more subpaths."""

    subpaths: list[list[tuple[float, float]]]
    stroke_color: tuple[float, float, float] | None = None
    fill_color: tuple[float, float, float] | None = None
    stroke_width: float | None = None
    fill_rule: str = "nonzero"
    stroke_alpha: float = 1.0
    fill_alpha: float = 1.0
    is_rectangle: bool = False

    @property
    def bbox(self) -> BoundingBox:
        xs: list[float] = []
        ys: list[float] = []
        for subpath in self.subpaths:
            for x, y in subpath:
                xs.append(x)
                ys.append(y)
        if not xs or not ys:
            return BoundingBox(0.0, 0.0, 0.0, 0.0)
        return BoundingBox(min(xs), min(ys), max(xs), max(ys))


@dataclass(slots=True)
class FormField:
    """Interactive form field extracted from a PDF page."""

    bbox: BoundingBox
    field_type: str
    name: str | None = None
    label: str | None = None
    value: str | None = None
    checked: bool | None = None
    options: list[str] = field(default_factory=list)
    tooltip: str | None = None
    read_only: bool = False
    multiline: bool = False


@dataclass(slots=True)
class Page:
    """Single PDF page with all extracted drawing primitives."""

    number: int
    width: float
    height: float
    text_blocks: list[TextBlock]
    images: list[Image]
    lines: list[Line]
    paths: list[Path] = field(default_factory=list)
    form_fields: list[FormField] = field(default_factory=list)
    links: list["Link"] = field(default_factory=list)
    annotations: list["PdfAnnotation"] = field(default_factory=list)
    tagged_roles: Sequence[str] | None = None

    def iter_text(self) -> Iterator[TextBlock]:
        return iter(self.text_blocks)


@dataclass(slots=True)
class PdfDocument:
    """Container returned by the IntelliPDF core parser."""

    pages: Sequence[Page]
    metadata: Mapping[str, str] | None = None
    tagged: bool = False
    outline: Sequence["OutlineNode"] | None = None

    def iter_pages(self) -> Iterator[Page]:
        return iter(self.pages)

    @property
    def page_count(self) -> int:
        return len(self.pages)


@dataclass(slots=True)
class Link:
    """Hyperlink annotation present on a page."""

    bbox: BoundingBox
    uri: str | None = None
    anchor: str | None = None
    tooltip: str | None = None
    kind: str = "external"  # "external", "internal", or "file"
    destination_page: int | None = None
    destination_top: float | None = None


@dataclass(slots=True)
class OutlineNode:
    """Hierarchical bookmark entry extracted from a PDF outline."""

    title: str
    page_number: int | None = None
    top: float | None = None
    anchor: str | None = None
    children: list["OutlineNode"] = field(default_factory=list)


@dataclass(slots=True)
class PdfAnnotation:
    """Free-form annotation such as a sticky note or comment."""

    bbox: BoundingBox
    text: str | None = None
    author: str | None = None
    subtype: str | None = None


