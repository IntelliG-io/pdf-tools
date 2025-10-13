"""Intermediate representation for the IntelliPDF → DOCX pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Sequence


@dataclass(slots=True)
class DocumentMetadata:
    """Metadata describing the source document."""

    title: str | None = None
    author: str | None = None
    subject: str | None = None
    description: str | None = None
    keywords: list[str] = field(default_factory=list)
    created: datetime | None = None
    modified: datetime | None = None
    language: str | None = None
    revision: str | None = None
    last_modified_by: str | None = None
    watermarks: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Run:
    """Inline text run with formatting attributes."""

    text: str
    break_type: str | None = None
    font_name: str | None = None
    font_size: float | None = None
    bold: bool = False
    italic: bool = False
    underline: bool = False
    color: str | None = None
    superscript: bool = False
    subscript: bool = False
    rtl: bool = False
    language: str | None = None
    vertical: bool = False
    style: str | None = None
    hyperlink_target: str | None = None
    hyperlink_anchor: str | None = None
    hyperlink_tooltip: str | None = None
    footnote_reference_id: int | None = None
    endnote_reference_id: int | None = None
    comment_reference_id: int | None = None
    comment_range_start_ids: list[int] = field(default_factory=list)
    comment_range_end_ids: list[int] = field(default_factory=list)


@dataclass(slots=True)
class Numbering:
    """List numbering information."""

    kind: str = "bullet"  # "bullet" or "ordered"
    level: int = 0
    format: str | None = None
    punctuation: str = "dot"
    marker: str | None = None
    indent: float | None = None


@dataclass(slots=True)
class Paragraph:
    """Block-level paragraph containing runs."""

    runs: list[Run] = field(default_factory=list)
    style: str | None = None
    role: str | None = None
    alignment: str | None = None
    numbering: Numbering | None = None
    metadata: dict[str, str] | None = None
    first_line_indent: float | None = None
    hanging_indent: float | None = None
    spacing_before: float | None = None
    spacing_after: float | None = None
    line_spacing: float | None = None
    keep_lines: bool = False
    keep_with_next: bool = False
    bidi: bool = False
    page_break_before: bool = False
    column_break_before: bool = False
    bookmarks: list[str] = field(default_factory=list)
    field_instruction: str | None = None
    background_color: str | None = None

    def text(self) -> str:
        return "".join(run.text for run in self.runs)


@dataclass(slots=True)
class Annotation:
    """User-visible annotation attached to the document."""

    text: str
    author: str | None = None
    kind: str | None = None

    def as_paragraph(self) -> Paragraph:
        role = "Annotation"
        run = Run(text=self.text)
        return Paragraph(runs=[run], role=role, style="Quote")


@dataclass(slots=True)
class Shape:
    """Simple geometric primitive description."""

    description: str
    bbox: Sequence[float]

    def as_paragraph(self) -> Paragraph:
        run = Run(text=self.description)
        return Paragraph(runs=[run], role="Shape", style="Caption")


@dataclass(slots=True)
class Picture:
    """Embedded raster image."""

    data: bytes
    width: float
    height: float
    mime_type: str | None = None
    name: str | None = None
    description: str | None = None


@dataclass(slots=True)
class Equation:
    """Mathematical content expressed as OMML or a fallback drawing."""

    omml: str | None = None
    mathml: str | None = None
    picture: Picture | None = None
    text: str | None = None
    description: str = "Equation"
    inline: bool = False
    bbox: tuple[float, float, float, float] | None = None
    metadata: dict[str, str] | None = None


@dataclass(slots=True)
class TableCell:
    """Single cell inside a table."""

    content: list["BlockElement"] = field(default_factory=list)
    row_span: int = 1
    col_span: int = 1
    row_span_continue: bool = False
    alignment: str | None = None
    vertical_alignment: str | None = None
    background_color: str | None = None
    borders: dict[str, str] | None = None


@dataclass(slots=True)
class TableRow:
    """Table row containing multiple cells."""

    cells: list[TableCell] = field(default_factory=list)
    is_header: bool = False


@dataclass(slots=True)
class Table:
    """Rectangular table structure."""

    rows: list[TableRow] = field(default_factory=list)
    width: float | None = None
    header_rows: int = 0
    column_widths: list[float] | None = None
    borders: dict[str, str] | None = None
    border_color: str | None = None
    alignment: str | None = None
    cell_padding: float | None = None


BlockElement = Paragraph | Table | Picture | Shape | Annotation | Equation


@dataclass(slots=True)
class Footnote:
    """Footnote entry extracted from a page."""

    id: int
    paragraphs: list[Paragraph] = field(default_factory=list)
    page_number: int | None = None
    marker: str | None = None


@dataclass(slots=True)
class Endnote:
    """Endnote entry produced from detected footnotes."""

    id: int
    paragraphs: list[Paragraph] = field(default_factory=list)
    page_number: int | None = None
    marker: str | None = None


@dataclass(slots=True)
class Comment:
    """Comment associated with a paragraph range."""

    id: int
    paragraphs: list[Paragraph] = field(default_factory=list)
    author: str | None = None
    text: str | None = None
    page_number: int | None = None


@dataclass(slots=True)
class OutlineItem:
    """Hierarchical outline entry used for bookmarks and TOC generation."""

    title: str
    anchor: str | None = None
    page_number: int | None = None
    level: int = 0
    children: list["OutlineItem"] = field(default_factory=list)


@dataclass(slots=True)
class HeaderFooter:
    """Header/footer container for a section."""

    content: list[BlockElement] = field(default_factory=list)
    metadata: dict[str, str] | None = None


@dataclass(slots=True)
class Section:
    """Document section that may span one or more pages."""

    page_width: float
    page_height: float
    margin_top: float = 72.0
    margin_bottom: float = 72.0
    margin_left: float = 72.0
    margin_right: float = 72.0
    elements: list[BlockElement] = field(default_factory=list)
    header: HeaderFooter | None = None
    footer: HeaderFooter | None = None
    first_page_header: HeaderFooter | None = None
    first_page_footer: HeaderFooter | None = None
    name: str | None = None
    start_page: int | None = None
    columns: int = 1
    column_spacing: float | None = None
    orientation: str = "portrait"

    def iter_elements(self) -> Iterable[BlockElement]:
        return iter(self.elements)


@dataclass(slots=True)
class Document:
    """Full logical document ready for OOXML emission."""

    metadata: DocumentMetadata
    sections: list[Section]
    tagged_pdf: bool = False
    page_count: int = 0
    outline: list[OutlineItem] = field(default_factory=list)
    footnotes: list[Footnote] = field(default_factory=list)
    endnotes: list[Endnote] = field(default_factory=list)
    comments: list[Comment] = field(default_factory=list)

    def iter_sections(self) -> Iterable[Section]:
        return iter(self.sections)


__all__ = [
    "Annotation",
    "BlockElement",
    "Comment",
    "Document",
    "DocumentMetadata",
    "Equation",
    "Endnote",
    "Footnote",
    "HeaderFooter",
    "Numbering",
    "OutlineItem",
    "Paragraph",
    "Picture",
    "Run",
    "Section",
    "Shape",
    "Table",
    "TableCell",
    "TableRow",
]
