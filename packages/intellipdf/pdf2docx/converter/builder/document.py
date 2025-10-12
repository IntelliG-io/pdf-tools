"""Document IR builder used by the converter pipeline."""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Iterable, Mapping, Sequence

from ...ir import (
    Annotation,
    BlockElement,
    Comment,
    Document,
    DocumentMetadata,
    Endnote,
    Equation,
    Footnote,
    Numbering,
    OutlineItem,
    Paragraph,
    Picture,
    Run,
    Section,
    Shape,
    Table,
)
from ...primitives import BoundingBox, Link, OutlineNode, Page, PdfAnnotation, TextBlock
from ..layout import (
    assign_headers_footers,
    collect_page_placements,
    infer_alignment,
    infer_columns,
    infer_style,
)
from ..lists import normalise_text_for_numbering, should_continue_across_pages
from .notes import (
    normalise_marker_text,
    process_comments,
    process_footnotes,
    record_superscript_marker,
)
from ..text import font_traits, indent_level, normalise_text_content
from .utils import (
    bbox_intersection_ratio,
    bbox_overlap_ratio,
    block_matches_position,
    column_index,
    estimate_margins,
    iter_outline_nodes,
    paragraph_bbox,
    paragraph_covers_position,
    same_geometry,
)

__all__ = ["DocumentBuilder"]


TOC_FIELD_INSTRUCTION = " ".join(
    [
        "TOC",
        "\\" + 'o "1-3"',
        "\\" + "h",
        "\\" + "z",
        "\\" + "u",
    ]
)


class DocumentBuilder:
    """Incrementally builds the intermediate representation document."""

    def __init__(
        self,
        metadata: DocumentMetadata,
        *,
        strip_whitespace: bool,
        include_outline_toc: bool = True,
        generate_toc_field: bool = True,
        footnotes_as_endnotes: bool = False,
    ) -> None:
        self.metadata = metadata
        self._strip_whitespace = strip_whitespace
        self._sections: list[Section] = []
        self._current_section: Section | None = None
        self._pending_paragraph: Paragraph | None = None
        self._pending_continue: bool = False
        self._previous_block: TextBlock | None = None
        self._previous_page_number: int | None = None
        self._current_page_number: int | None = None
        self._font_samples: list[float] = []
        self._page_elements: defaultdict[int, list[BlockElement]] = defaultdict(list)
        self._page_section_map: dict[int, Section] = {}
        self._list_stack: list[tuple[float, str]] = []
        self._page_break_pending: bool = False
        self._column_break_pending: bool = False
        self._current_column_index: int | None = None
        self._columns_seen: set[int] = set()
        self._last_emitted_page: int | None = None
        self._links_by_page: defaultdict[int, list[Link]] = defaultdict(list)
        self._bookmarks_by_page: defaultdict[int, list[tuple[float | None, str]]] = defaultdict(list)
        self._assigned_bookmarks: set[str] = set()
        self._registered_destinations: set[str] = set()
        self._include_outline_toc = include_outline_toc
        self._generate_toc_field = generate_toc_field
        self._outline_nodes: list[OutlineNode] = []
        self._outline_items: list[OutlineItem] = []
        self._toc_inserted = False
        self._annotations_by_page: defaultdict[int, list[PdfAnnotation]] = defaultdict(list)
        self._page_dimensions: dict[int, tuple[float, float]] = {}
        self._footnote_markers_by_page: defaultdict[
            int, list[tuple[str, Paragraph, Run]]
        ] = defaultdict(list)
        self._footnotes: list[Footnote] = []
        self._endnotes: list[Endnote] = []
        self._comments: list[Comment] = []
        self._footnotes_as_endnotes = footnotes_as_endnotes

    def ensure_section(self, page: Page, page_number: int) -> Section:
        orientation = "landscape" if page.width > page.height else "portrait"
        margins = estimate_margins(page)
        columns, spacing = infer_columns(page)
        if self._current_section is not None and same_geometry(
            self._current_section,
            page,
            margins,
            columns,
            spacing,
            orientation,
        ):
            self._current_page_number = page_number
            self._page_section_map[page_number] = self._current_section
            if self._last_emitted_page is not None and page_number != self._last_emitted_page:
                self._page_break_pending = True
            else:
                self._page_break_pending = False
            self._column_break_pending = False
            self._current_column_index = None
            self._columns_seen.clear()
            return self._current_section
        self.flush_pending(self._current_section)
        self._clear_list_state()
        section = Section(
            page_width=page.width,
            page_height=page.height,
            margin_top=margins[0],
            margin_bottom=margins[1],
            margin_left=margins[2],
            margin_right=margins[3],
            start_page=page_number,
        )
        section.orientation = orientation
        section.columns = columns
        section.column_spacing = spacing
        self._sections.append(section)
        self._current_section = section
        self._previous_block = None
        self._previous_page_number = None
        self._current_page_number = page_number
        self._page_section_map[page_number] = section
        self._page_break_pending = False
        self._column_break_pending = False
        self._current_column_index = None
        self._columns_seen.clear()
        return section

    def register_outline(self, outline: Sequence[OutlineNode] | None) -> None:
        if not outline:
            self._outline_nodes = []
            return
        self._outline_nodes = [deepcopy(node) for node in outline]
        for node in self._iter_outline_nodes(self._outline_nodes):
            if node.anchor and node.page_number is not None:
                self._register_outline_destination(node.anchor, node.page_number, node.top)

    def add_text_block(self, section: Section, block: TextBlock, page_number: int) -> None:
        self._current_page_number = page_number
        text = normalise_text_content(block.text, strip=self._strip_whitespace)
        if not text:
            self._clear_list_state()
            self._finalise_pending_spacing(None, page_number)
            self._pending_continue = False
            self.flush_pending(section)
            self._previous_block = block
            self._previous_page_number = page_number
            return

        working_block = deepcopy(block)
        working_block.text = text
        column_index_value: int | None = None
        if section.columns > 1:
            column_index_value = column_index(working_block, section)
            if column_index_value is not None:
                if column_index_value not in self._columns_seen and self._columns_seen:
                    self._column_break_pending = True
                if column_index_value not in self._columns_seen:
                    self._columns_seen.add(column_index_value)
        link = self._link_for_block(working_block, page_number)
        if link and link.kind == "internal" and link.anchor and link.destination_page is not None:
            self._register_internal_link_destination(link)
        content, numbering = normalise_text_for_numbering(working_block, section)
        if self._pending_paragraph and self._can_continue(block, page_number):
            self._append_run(content, working_block, page_number, column_index_value, link)
        else:
            if self._pending_paragraph is not None:
                self._finalise_pending_spacing(working_block, page_number)
            self.flush_pending(section)
            self._start_paragraph(
                content,
                working_block,
                numbering,
                section,
                page_number,
                column_index_value,
                link,
            )

        self._pending_continue = should_continue_across_pages(content, block.role)
        self._previous_block = block
        self._previous_page_number = page_number

    def add_element(
        self,
        section: Section,
        element: Paragraph | Table | Picture | Shape | Annotation | Equation,
        page_number: int | None = None,
    ) -> None:
        self.flush_pending(section)
        self._emit_pending_breaks(section)
        if page_number is not None and isinstance(element, Equation):
            metadata = element.metadata or {}
            metadata.setdefault("start_page", str(page_number))
            metadata.setdefault("end_page", str(page_number))
            element.metadata = metadata
        section.elements.append(element)
        if page_number is not None:
            self._current_page_number = page_number
        self._register_element(element)
        if isinstance(element, Paragraph):
            if element.numbering is None:
                self._clear_list_state()
            self._pending_paragraph = None
            self._pending_continue = False
        else:
            self._clear_list_state()

    def flush_pending(self, section: Section | None) -> None:
        if section is not None and self._pending_paragraph is not None:
            self._finalise_pending_spacing(None, None)
            section.elements.append(self._pending_paragraph)
            self._register_element(self._pending_paragraph)
        self._pending_paragraph = None
        self._pending_continue = False

    def end_page(self, section: Section | None) -> None:
        if not self._pending_continue:
            self._finalise_pending_spacing(None, None)
        if not self._pending_continue:
            self.flush_pending(section)
        if not self._pending_continue:
            self._previous_block = None
            self._previous_page_number = None

    def _finalise_outline(self) -> None:
        if not self._outline_nodes:
            self._outline_items = []
            return
        items = self._convert_outline_nodes(self._outline_nodes)
        self._outline_items = items
        if not items:
            return
        if self._include_outline_toc and not self._toc_inserted and self._sections:
            toc_paragraphs = self._build_toc_paragraphs(items)
            if toc_paragraphs:
                first_section = self._sections[0]
                first_section.elements = list(toc_paragraphs) + first_section.elements
                self._toc_inserted = True

    def build(self, *, tagged: bool, page_count: int) -> Document:
        self.flush_pending(self._current_section)
        self._finalise_outline()
        document = Document(
            metadata=self.metadata,
            sections=self._sections,
            tagged_pdf=tagged,
            page_count=page_count,
            outline=self._outline_items,
        )
        process_comments(self, document)
        process_footnotes(self, document)
        document.comments = list(self._comments)
        document.footnotes = list(self._footnotes)
        document.endnotes = list(self._endnotes)
        assign_headers_footers(document, self._page_elements, self._page_section_map)
        self._detect_watermarks(document)
        return document

    def _detect_watermarks(self, document: Document) -> None:
        total_pages = document.page_count or len(self._page_elements)
        if total_pages <= 1:
            return
        centre_threshold = 0.2
        required = max(2, int(total_pages * 0.8))
        candidates: dict[tuple[str, int, int], list[tuple[int, Paragraph]]] = defaultdict(list)
        for page_number, elements in self._page_elements.items():
            page_width, page_height = self._page_dimensions.get(page_number, (0.0, 0.0))
            if page_width <= 0 or page_height <= 0:
                continue
            for element in elements:
                if not isinstance(element, Paragraph):
                    continue
                text = element.text().strip()
                if not text:
                    continue
                metadata = element.metadata or {}
                try:
                    left = float(metadata.get("bbox_left"))
                    right = float(metadata.get("bbox_right"))
                    top = float(metadata.get("bbox_top"))
                    bottom = float(metadata.get("bbox_bottom"))
                except (TypeError, ValueError):
                    continue
                width = right - left
                height = top - bottom
                if width <= 0 or height <= 0:
                    continue
                cx = left + width / 2
                cy = bottom + height / 2
                if not (
                    page_width * centre_threshold <= cx <= page_width * (1 - centre_threshold)
                    and page_height * centre_threshold <= cy <= page_height * (1 - centre_threshold)
                ):
                    continue
                opacity = metadata.get("opacity")
                if opacity is not None:
                    try:
                        if float(opacity) > 0.8:
                            continue
                    except ValueError:
                        pass
                key = (
                    text,
                    int(round((cx / page_width) * 100)),
                    int(round((cy / page_height) * 100)),
                )
                candidates[key].append((page_number, element))
        for entries in candidates.values():
            pages = {page for page, _ in entries}
            if len(pages) < required:
                continue
            watermark_text = entries[0][1].text.strip()
            if watermark_text and watermark_text not in document.metadata.watermarks:
                document.metadata.watermarks.append(watermark_text)
            for _, paragraph in entries:
                metadata = paragraph.metadata or {}
                metadata["watermark"] = "true"
                paragraph.metadata = metadata

    def process_page(self, page: Page, page_number: int) -> None:
        section = self.ensure_section(page, page_number)
        self._links_by_page[page.number] = list(page.links)
        self._annotations_by_page[page.number] = list(page.annotations)
        self._page_dimensions[page.number] = (page.width, page.height)
        for link in page.links:
            if link.kind == "internal" and link.anchor and link.destination_page is not None:
                self._register_internal_link_destination(link)
        placements = collect_page_placements(page, self._strip_whitespace)
        for _, _, kind, payload in placements:
            if kind == "text":
                self.add_text_block(section, payload, page_number)  # type: ignore[arg-type]
            else:
                self.add_element(section, payload, page_number)
        self.end_page(section)
        self._last_emitted_page = page_number

    def _can_continue(self, block: TextBlock, page_number: int) -> bool:
        if self._pending_paragraph is None or self._previous_block is None:
            return False
        if block.vertical or self._previous_block.vertical:
            return False
        if block.role and self._pending_paragraph.role and block.role != self._pending_paragraph.role:
            return False
        if self._current_section is not None and self._current_section.columns > 1:
            previous_column = column_index(self._previous_block, self._current_section)
            current_column = column_index(block, self._current_section)
            if (
                previous_column is not None
                and current_column is not None
                and previous_column != current_column
            ):
                return False
        if self._previous_page_number == page_number:
            baseline = block.font_size or self._previous_block.font_size or 12.0
            vertical_gap = self._previous_block.bbox.bottom - block.bbox.top
            if vertical_gap > baseline * 1.2:
                return False
        else:
            if not self._pending_continue or self._current_section is None:
                return False
            baseline = block.font_size or self._previous_block.font_size or 12.0
            tolerance = max(baseline * 2, 24.0)
            lower_bound = self._current_section.margin_bottom + tolerance
            upper_bound = self._current_section.page_height - (
                self._current_section.margin_top + tolerance
            )
            previous_top = self._previous_block.bbox.top
            if previous_top < lower_bound or previous_top > upper_bound:
                return False
            if block.bbox.top < upper_bound:
                return False
        return True

    def _start_paragraph(
        self,
        text: str,
        block: TextBlock,
        numbering: Numbering | None,
        section: Section,
        page_number: int,
        column_index: int | None,
        link: Link | None,
    ) -> None:
        bold, italic, underline = font_traits(block.font_name)
        run = Run(
            text=text,
            font_name=block.font_name,
            font_size=block.font_size,
            bold=block.bold or bold,
            italic=block.italic or italic,
            underline=block.underline or underline,
            color=block.color or "000000",
            superscript=block.superscript,
            subscript=block.subscript,
            rtl=block.rtl,
            language=block.language,
            vertical=block.vertical,
        )
        self._apply_link_to_run(run, link)
        paragraph = Paragraph(runs=[run], role=block.role, numbering=numbering, bidi=block.rtl)
        metadata = {
            "start_page": str(page_number),
            "end_page": str(page_number),
            "bbox_top": f"{block.bbox.top:.2f}",
            "bbox_bottom": f"{block.bbox.bottom:.2f}",
            "bbox_left": f"{block.bbox.left:.2f}",
            "bbox_right": f"{block.bbox.right:.2f}",
        }
        if block.opacity is not None:
            metadata["opacity"] = f"{max(0.0, min(block.opacity, 1.0)):.3f}"
        paragraph.metadata = metadata
        if block.background_color:
            paragraph.background_color = block.background_color
        self._attach_bookmarks_from_block(paragraph, block, page_number)
        if self._page_break_pending:
            paragraph.page_break_before = True
            self._page_break_pending = False
        if self._column_break_pending and column_index is not None:
            paragraph.column_break_before = True
            self._column_break_pending = False
        indent = indent_level(block, section)
        if numbering:
            if numbering.kind == "ordered" and numbering.format is None:
                numbering.format = "decimal"
            numbering.indent = indent
            numbering.level = self._assign_list_level(indent, numbering)
        else:
            self._clear_list_state()
        self._apply_paragraph_formatting(paragraph, block, section, numbering, indent)
        if block.font_size:
            self._font_samples.append(block.font_size)
        self._pending_paragraph = paragraph
        if column_index is not None:
            self._current_column_index = column_index
        record_superscript_marker(self, run, block, page_number)

    def _append_run(
        self,
        text: str,
        block: TextBlock,
        page_number: int | None = None,
        column_index: int | None = None,
        link: Link | None = None,
    ) -> None:
        effective_page = (
            page_number
            if page_number is not None
            else self._current_page_number
            if self._current_page_number is not None
            else self._previous_page_number
        )
        if effective_page is None:
            effective_page = 0
        if self._pending_paragraph is None:
            if self._current_section is None:
                raise RuntimeError("Cannot append run without an active section")
            self._start_paragraph(
                text,
                block,
                None,
                self._current_section,
                effective_page,
                column_index,
                link,
            )
            return
        last_run = self._pending_paragraph.runs[-1]
        if (
            not last_run.vertical
            and not block.vertical
            and last_run.text
            and not last_run.text.endswith(" ")
            and not text.startswith(" ")
        ):
            last_run.text += " "
        if (
            not last_run.vertical
            and last_run.text.endswith("-")
            and text
            and text[0].islower()
        ):
            last_run.text = last_run.text[:-1]
        metadata = self._pending_paragraph.metadata or {}
        start_page = int(metadata.get("start_page", effective_page)) if effective_page is not None else 0
        end_page = int(metadata.get("end_page", start_page))
        if (
            self._page_break_pending
            and effective_page is not None
            and end_page != effective_page
        ):
            self._pending_paragraph.runs.append(Run(text="", break_type="page"))
            self._page_break_pending = False
        if (
            self._column_break_pending
            and column_index is not None
            and column_index != self._current_column_index
        ):
            self._pending_paragraph.runs.append(Run(text="", break_type="column"))
            self._column_break_pending = False
        bold, italic, underline = font_traits(block.font_name)
        self._pending_paragraph.runs.append(
            Run(
                text=text,
                font_name=block.font_name,
                font_size=block.font_size,
                bold=block.bold or bold,
                italic=block.italic or italic,
                underline=block.underline or underline,
                color=block.color or "000000",
                superscript=block.superscript,
                subscript=block.subscript,
                rtl=block.rtl,
                language=block.language,
                vertical=block.vertical,
            )
        )
        self._apply_link_to_run(self._pending_paragraph.runs[-1], link)
        self._pending_paragraph.bidi = self._pending_paragraph.bidi or block.rtl
        if block.background_color and not self._pending_paragraph.background_color:
            self._pending_paragraph.background_color = block.background_color
        metadata["end_page"] = str(effective_page)
        if block.opacity is not None:
            new_opacity = max(0.0, min(block.opacity, 1.0))
            current_opacity = metadata.get("opacity")
            if current_opacity is None:
                metadata["opacity"] = f"{new_opacity:.3f}"
            else:
                try:
                    if new_opacity < float(current_opacity):
                        metadata["opacity"] = f"{new_opacity:.3f}"
                except ValueError:
                    metadata["opacity"] = f"{new_opacity:.3f}"
        try:
            current_top = float(metadata.get("bbox_top", block.bbox.top))
        except (TypeError, ValueError):
            current_top = block.bbox.top
        try:
            current_bottom = float(metadata.get("bbox_bottom", block.bbox.bottom))
        except (TypeError, ValueError):
            current_bottom = block.bbox.bottom
        try:
            current_left = float(metadata.get("bbox_left", block.bbox.left))
        except (TypeError, ValueError):
            current_left = block.bbox.left
        try:
            current_right = float(metadata.get("bbox_right", block.bbox.right))
        except (TypeError, ValueError):
            current_right = block.bbox.right
        metadata["bbox_top"] = f"{max(current_top, block.bbox.top):.2f}"
        metadata["bbox_bottom"] = f"{min(current_bottom, block.bbox.bottom):.2f}"
        metadata["bbox_left"] = f"{min(current_left, block.bbox.left):.2f}"
        metadata["bbox_right"] = f"{max(current_right, block.bbox.right):.2f}"
        self._pending_paragraph.metadata = metadata
        if column_index is not None:
            self._current_column_index = column_index
        self._attach_bookmarks_from_block(self._pending_paragraph, block, effective_page)
        record_superscript_marker(
            self, self._pending_paragraph.runs[-1], block, effective_page
        )

    def _register_element(self, element: BlockElement) -> None:
        if self._current_page_number is None:
            return
        if isinstance(element, Paragraph):
            metadata = element.metadata or {}
            start = int(metadata.get("start_page", self._current_page_number))
            end = int(metadata.get("end_page", start))
            for page in range(start, end + 1):
                self._page_elements[page].append(element)
        else:
            self._page_elements[self._current_page_number].append(element)

    def _iter_outline_nodes(self, nodes: Sequence[OutlineNode]) -> Iterable[OutlineNode]:
        for node in nodes:
            yield node
            if node.children:
                yield from self._iter_outline_nodes(node.children)

    def _convert_outline_nodes(
        self, nodes: Sequence[OutlineNode], level: int = 0
    ) -> list[OutlineItem]:
        items: list[OutlineItem] = []
        for node in nodes:
            anchor = node.anchor if node.anchor in self._assigned_bookmarks else None
            item = OutlineItem(
                title=node.title,
                anchor=anchor,
                page_number=node.page_number,
                level=level,
                children=self._convert_outline_nodes(node.children, level + 1)
                if node.children
                else [],
            )
            items.append(item)
        return items

    def _build_toc_paragraphs(self, outline: Sequence[OutlineItem]) -> list[Paragraph]:
        paragraphs: list[Paragraph] = []
        heading = Paragraph(runs=[Run(text="Table of Contents")], style="TOCHeading")
        heading.keep_with_next = True
        heading.metadata = {"generated": "toc"}
        paragraphs.append(heading)
        if self._generate_toc_field:
            field_paragraph = Paragraph(
                runs=[
                    Run(
                        text="Update this field after opening to refresh the table of contents."
                    )
                ],
                style="TOCHeading",
            )
            field_paragraph.field_instruction = TOC_FIELD_INSTRUCTION
            field_paragraph.metadata = {"generated": "toc-field"}
            paragraphs.append(field_paragraph)

        def append_entries(items: Sequence[OutlineItem], depth: int) -> None:
            for item in items:
                title = item.title or "Untitled"
                run = Run(text=title)
                if item.anchor:
                    run.hyperlink_anchor = item.anchor
                    run.style = "Hyperlink"
                paragraph = Paragraph(
                    runs=[run],
                    style=f"TOC{min(depth + 1, 9)}",
                )
                paragraph.metadata = {"generated": "toc-entry", "toc_level": str(depth)}
                paragraphs.append(paragraph)
                if item.children:
                    append_entries(item.children, depth + 1)

        append_entries(outline, 0)
        return paragraphs

    def _clear_list_state(self) -> None:
        self._list_stack.clear()

    def _link_for_block(self, block: TextBlock, page_number: int) -> Link | None:
        candidates = self._links_by_page.get(page_number)
        if not candidates:
            return None
        best_score = 0.0
        best_link: Link | None = None
        for link in candidates:
            score = bbox_overlap_ratio(block, link.bbox)
            if score <= 0.05:
                continue
            if score > best_score:
                best_score = score
                best_link = link
        return best_link

    def _apply_link_to_run(self, run: Run, link: Link | None) -> None:
        if link is None:
            return
        if link.uri:
            run.hyperlink_target = link.uri
            run.style = run.style or "Hyperlink"
        if link.anchor:
            run.hyperlink_anchor = link.anchor
            run.style = run.style or "Hyperlink"
        if link.tooltip:
            run.hyperlink_tooltip = link.tooltip

    def _register_internal_link_destination(self, link: Link) -> None:
        anchor = link.anchor
        if not anchor or link.destination_page is None:
            return
        if anchor in self._assigned_bookmarks or anchor in self._registered_destinations:
            return
        if self._assign_bookmark_to_existing(link.destination_page, link.destination_top, anchor):
            self._registered_destinations.add(anchor)
            return
        self._bookmarks_by_page[link.destination_page].append((link.destination_top, anchor))
        self._registered_destinations.add(anchor)

    def _register_outline_destination(
        self, anchor: str, page_number: int, top: float | None
    ) -> None:
        if anchor in self._assigned_bookmarks or anchor in self._registered_destinations:
            return
        if self._assign_bookmark_to_existing(page_number, top, anchor):
            self._registered_destinations.add(anchor)
            return
        self._bookmarks_by_page[page_number].append((top, anchor))
        self._registered_destinations.add(anchor)

    def _assign_bookmark_to_existing(
        self, page_number: int, top: float | None, anchor: str
    ) -> bool:
        elements = self._page_elements.get(page_number)
        if not elements:
            return False
        for element in elements:
            if isinstance(element, Paragraph) and paragraph_covers_position(
                element, page_number, top
            ):
                self._attach_bookmark(element, anchor)
                return True
        return False

    def _attach_bookmark(self, paragraph: Paragraph, anchor: str) -> None:
        existing = getattr(paragraph, "bookmarks", None)
        if existing is None:
            paragraph.bookmarks = [anchor]
        else:
            if anchor in existing:
                return
            existing.append(anchor)
        self._assigned_bookmarks.add(anchor)

    def _attach_bookmarks_from_block(
        self, paragraph: Paragraph, block: TextBlock, page_number: int
    ) -> None:
        pending = self._bookmarks_by_page.get(page_number)
        if not pending:
            return
        remaining: list[tuple[float | None, str]] = []
        for top, anchor in pending:
            if anchor in self._assigned_bookmarks:
                continue
            if top is None or block_matches_position(block, top):
                self._attach_bookmark(paragraph, anchor)
            else:
                remaining.append((top, anchor))
        self._bookmarks_by_page[page_number] = remaining

    def _emit_pending_breaks(self, section: Section) -> None:
        if not self._page_break_pending and not self._column_break_pending:
            return
        metadata_page = self._current_page_number
        if metadata_page is None:
            metadata_page = self._last_emitted_page or 0
        paragraph = Paragraph(
            runs=[],
            page_break_before=self._page_break_pending,
            column_break_before=self._column_break_pending,
            metadata={
                "start_page": str(metadata_page),
                "end_page": str(metadata_page),
            },
        )
        section.elements.append(paragraph)
        self._register_element(paragraph)
        self._page_break_pending = False
        self._column_break_pending = False

    def _assign_list_level(self, indent: float, numbering: Numbering) -> int:
        format_key = "bullet"
        if numbering.kind == "ordered":
            base_format = numbering.format or "decimal"
            punctuation = numbering.punctuation or "dot"
            format_key = f"{base_format}:{punctuation}"
        if not self._list_stack:
            self._list_stack.append((indent, format_key))
            return 0
        tolerance = 6.0
        for level, (existing_indent, existing_format) in enumerate(self._list_stack):
            if abs(indent - existing_indent) <= tolerance and existing_format == format_key:
                return level
        if indent > self._list_stack[-1][0] + tolerance:
            if len(self._list_stack) < 9:
                self._list_stack.append((indent, format_key))
            return min(len(self._list_stack) - 1, 8)
        if len(self._list_stack) < 9:
            self._list_stack.append((indent, format_key))
        return min(len(self._list_stack) - 1, 8)

    def _apply_paragraph_formatting(
        self,
        paragraph: Paragraph,
        block: TextBlock,
        section: Section,
        numbering: Numbering | None,
        indent: float,
    ) -> None:
        if numbering:
            paragraph.hanging_indent = None
            paragraph.first_line_indent = None
        else:
            paragraph.first_line_indent = indent
            paragraph.hanging_indent = None
        if self._previous_block is not None and self._previous_page_number == self._current_page_number:
            gap = self._previous_block.bbox.bottom - block.bbox.top
            baseline = block.font_size or self._previous_block.font_size or 12.0
            if gap > baseline * 0.5:
                paragraph.spacing_before = gap
        if block.font_size and block.bbox.height() > 0:
            ratio = block.bbox.height() / max(block.font_size, 0.1)
            paragraph.line_spacing = round(max(1.0, min(ratio, 2.5)), 2)
        else:
            paragraph.line_spacing = 1.2
        paragraph.alignment = infer_alignment(block, section)
        paragraph.style = infer_style(block, numbering, self._font_samples)
        if paragraph.style and paragraph.style.startswith("Heading"):
            paragraph.keep_lines = True
            paragraph.keep_with_next = True
        elif paragraph.style == "Title":
            paragraph.keep_lines = True
            paragraph.keep_with_next = True
        paragraph.bidi = paragraph.bidi or block.rtl
        if block.background_color:
            paragraph.background_color = block.background_color

    def _finalise_pending_spacing(
        self,
        next_block: TextBlock | None,
        next_page_number: int | None,
    ) -> None:
        if self._pending_paragraph is None:
            return
        if self._pending_paragraph.spacing_after is not None:
            return
        last_block = self._previous_block
        if last_block is None:
            return
        baseline = (
            last_block.font_size
            or self._pending_paragraph.runs[-1].font_size
            or (self._font_samples[-1] if self._font_samples else None)
            or 12.0
        )
        spacing_after = 0.0
        if (
            next_block is not None
            and next_page_number is not None
            and next_page_number == self._previous_page_number
        ):
            gap = last_block.bbox.bottom - next_block.bbox.top
            if gap > baseline * 0.5:
                spacing_after = gap
        else:
            spacing_after = baseline * 0.6
        if spacing_after > 0:
            self._pending_paragraph.spacing_after = spacing_after
