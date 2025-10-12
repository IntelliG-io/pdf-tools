"""XML element builders for DOCX output."""

from __future__ import annotations

import re
from xml.etree.ElementTree import Element, SubElement, fromstring
from xml.etree.ElementTree import ParseError

from typing import Sequence

from copy import deepcopy

from ..ir import (
    Annotation,
    BlockElement,
    Comment,
    Document,
    Endnote,
    Equation,
    Footnote,
    HeaderFooter,
    Paragraph,
    Picture,
    Section,
    Shape,
    Table,
    TableCell,
)
from .numbering import NUMBERING_IDS, PUNCTUATION_MARKERS
from .relationships import RelationshipManager
from .utils import emus, serialize, twips
from .namespaces import XML_NS

__all__ = [
    "append_block",
    "build_comments_xml",
    "build_document_xml",
    "build_equation_paragraph",
    "build_endnotes_xml",
    "build_footnotes_xml",
    "build_header_footer_xml",
    "build_paragraph_element",
    "build_section_properties",
    "build_table_element",
]


class BookmarkState:
    """Tracks bookmark identifiers for a document part."""

    def __init__(self) -> None:
        self._next_id = 1

    def allocate(self) -> int:
        bookmark_id = self._next_id
        self._next_id += 1
        return bookmark_id


def _sanitise_bookmark_name(name: str) -> str:
    cleaned = [ch for ch in name if ch.isalnum() or ch in {"_", "-", "."}]
    if not cleaned:
        cleaned = ["bookmark"]
    result = "".join(cleaned)
    if result[0].isdigit():
        result = f"bookmark_{result}"
    return result[:40]


def build_paragraph_element(
    paragraph: Paragraph, relationships: RelationshipManager, bookmark_state: BookmarkState
) -> Element:
    w_ns = f"{{{XML_NS['w']}}}"
    r_ns = f"{{{XML_NS['r']}}}"
    p = Element(f"{w_ns}p")
    if (
        paragraph.style
        or paragraph.alignment
        or paragraph.numbering
        or paragraph.role
        or paragraph.first_line_indent is not None
        or paragraph.hanging_indent is not None
        or paragraph.spacing_before is not None
        or paragraph.spacing_after is not None
        or paragraph.line_spacing is not None
        or paragraph.keep_lines
        or paragraph.keep_with_next
        or paragraph.bidi
        or paragraph.page_break_before
        or paragraph.background_color
    ):
        p_pr = SubElement(p, f"{w_ns}pPr")
        style_name = paragraph.style
        if style_name is None and paragraph.role:
            role = paragraph.role.upper()
            if role.startswith("H") and role[1:].isdigit():
                style_name = f"Heading{role[1:]}"
            elif role in {"TITLE", "SUBTITLE"}:
                style_name = "Title" if role == "TITLE" else "Subtitle"
            elif role in {"LI", "LBODY", "LBL", "L"}:
                style_name = "ListParagraph"
        if style_name:
            SubElement(p_pr, f"{w_ns}pStyle", {f"{w_ns}val": style_name})
        if paragraph.numbering:
            num_pr = SubElement(p_pr, f"{w_ns}numPr")
            level = max(0, min(paragraph.numbering.level, 8))
            SubElement(num_pr, f"{w_ns}ilvl", {f"{w_ns}val": str(level)})
            if paragraph.numbering.kind == "bullet":
                key = ("bullet", None, None)
            else:
                format_name = paragraph.numbering.format or "decimal"
                punctuation = paragraph.numbering.punctuation or "dot"
                if punctuation not in PUNCTUATION_MARKERS:
                    punctuation = "dot"
                key = ("ordered", format_name, punctuation)
            num_id = NUMBERING_IDS.get(key)
            if num_id is None:
                num_id = NUMBERING_IDS[("ordered", "decimal", "dot")]
            SubElement(num_pr, f"{w_ns}numId", {f"{w_ns}val": str(num_id)})
        if paragraph.alignment:
            alignment = paragraph.alignment.lower()
            SubElement(p_pr, f"{w_ns}jc", {f"{w_ns}val": alignment})
        if (
            paragraph.first_line_indent is not None
            or paragraph.hanging_indent is not None
        ):
            attrs: dict[str, str] = {}
            if paragraph.first_line_indent is not None:
                attrs[f"{w_ns}firstLine"] = str(twips(paragraph.first_line_indent))
            if paragraph.hanging_indent is not None:
                attrs[f"{w_ns}hanging"] = str(twips(paragraph.hanging_indent))
            if attrs:
                SubElement(p_pr, f"{w_ns}ind", attrs)
        if (
            paragraph.spacing_before is not None
            or paragraph.spacing_after is not None
            or paragraph.line_spacing is not None
        ):
            spacing_attrs: dict[str, str] = {}
            if paragraph.spacing_before is not None:
                spacing_attrs[f"{w_ns}before"] = str(twips(paragraph.spacing_before))
            if paragraph.spacing_after is not None:
                spacing_attrs[f"{w_ns}after"] = str(twips(paragraph.spacing_after))
            if paragraph.line_spacing is not None:
                spacing_attrs[f"{w_ns}line"] = str(int(paragraph.line_spacing * 240))
                spacing_attrs[f"{w_ns}lineRule"] = "auto"
            if spacing_attrs:
                SubElement(p_pr, f"{w_ns}spacing", spacing_attrs)
        if paragraph.keep_lines:
            SubElement(p_pr, f"{w_ns}keepLines")
        if paragraph.keep_with_next:
            SubElement(p_pr, f"{w_ns}keepNext")
        if paragraph.bidi:
            SubElement(p_pr, f"{w_ns}bidi")
        if paragraph.page_break_before:
            SubElement(p_pr, f"{w_ns}pageBreakBefore")
        if paragraph.background_color:
            fill = paragraph.background_color.replace("#", "").upper()
            if len(fill) == 6:
                SubElement(
                    p_pr,
                    f"{w_ns}shd",
                    {
                        f"{w_ns}val": "clear",
                        f"{w_ns}color": "auto",
                        f"{w_ns}fill": fill,
                    },
                )
    if paragraph.column_break_before:
        run = SubElement(p, f"{w_ns}r")
        SubElement(run, f"{w_ns}br", {f"{w_ns}type": "column"})
    bookmark_ids: list[tuple[int, str]] = []
    if getattr(paragraph, "bookmarks", None):
        seen: set[str] = set()
        for name in paragraph.bookmarks:
            sanitized = _sanitise_bookmark_name(name)
            if sanitized in seen:
                continue
            seen.add(sanitized)
            bookmark_id = bookmark_state.allocate()
            SubElement(
                p,
                f"{w_ns}bookmarkStart",
                {f"{w_ns}id": str(bookmark_id), f"{w_ns}name": sanitized},
            )
            bookmark_ids.append((bookmark_id, sanitized))
    field_instruction = paragraph.field_instruction
    run_parent = p
    if field_instruction:
        run_parent = SubElement(p, f"{w_ns}fldSimple", {f"{w_ns}instr": field_instruction})
    if not paragraph.runs:
        if run_parent is p and not paragraph.column_break_before:
            SubElement(p, f"{w_ns}r")
        else:
            SubElement(run_parent, f"{w_ns}r")
        for bookmark_id, _ in bookmark_ids:
            SubElement(p, f"{w_ns}bookmarkEnd", {f"{w_ns}id": str(bookmark_id)})
        return p
    for run in paragraph.runs:
        start_ids = getattr(run, "comment_range_start_ids", []) or []
        end_ids = getattr(run, "comment_range_end_ids", []) or []
        for comment_id in start_ids:
            SubElement(p, f"{w_ns}commentRangeStart", {f"{w_ns}id": str(comment_id)})
        run_element = build_run_element(run)
        target = getattr(run, "hyperlink_target", None)
        anchor = getattr(run, "hyperlink_anchor", None)
        tooltip = getattr(run, "hyperlink_tooltip", None)
        if field_instruction:
            run_parent.append(run_element)
        elif target or anchor:
            hyperlink = Element(f"{w_ns}hyperlink")
            if anchor:
                hyperlink.set(f"{w_ns}anchor", anchor)
            if target:
                rid = relationships.register_hyperlink(target)
                hyperlink.set(f"{r_ns}id", rid)
            if tooltip:
                hyperlink.set(f"{w_ns}tooltip", tooltip)
            hyperlink.append(run_element)
            p.append(hyperlink)
        else:
            p.append(run_element)
        for comment_id in end_ids:
            SubElement(p, f"{w_ns}commentRangeEnd", {f"{w_ns}id": str(comment_id)})
    for bookmark_id, _ in bookmark_ids:
        SubElement(p, f"{w_ns}bookmarkEnd", {f"{w_ns}id": str(bookmark_id)})
    return p


def build_run_element(run) -> Element:
    from ..ir import Run  # local import to avoid circular dependency

    w_ns = f"{{{XML_NS['w']}}}"
    r = Element(f"{w_ns}r")
    needs_props = (
        run.font_name
        or run.font_size
        or run.bold
        or run.italic
        or run.underline
        or run.color
        or run.superscript
        or run.subscript
        or run.rtl
        or run.language
        or run.style
        or run.footnote_reference_id is not None
        or run.endnote_reference_id is not None
        or run.comment_reference_id is not None
    )
    r_pr = None
    if needs_props:
        r_pr = SubElement(r, f"{w_ns}rPr")
        if run.style:
            SubElement(r_pr, f"{w_ns}rStyle", {f"{w_ns}val": run.style})
        if run.font_name:
            font_name = run.font_name
            try:
                font_name = re.sub(r"^[A-Z]{6,7}\+", "", font_name)
            except Exception:
                pass
            SubElement(
                r_pr,
                f"{w_ns}rFonts",
                {
                    f"{w_ns}ascii": font_name,
                    f"{w_ns}hAnsi": font_name,
                    f"{w_ns}cs": font_name,
                },
            )
        if run.font_size:
            SubElement(r_pr, f"{w_ns}sz", {f"{w_ns}val": str(int(run.font_size * 2))})
        if run.bold:
            SubElement(r_pr, f"{w_ns}b")
        if run.italic:
            SubElement(r_pr, f"{w_ns}i")
        if run.underline:
            SubElement(r_pr, f"{w_ns}u", {f"{w_ns}val": "single"})
        if run.color:
            SubElement(r_pr, f"{w_ns}color", {f"{w_ns}val": run.color})
        if run.superscript:
            SubElement(r_pr, f"{w_ns}vertAlign", {f"{w_ns}val": "sup"})
        if run.subscript:
            SubElement(r_pr, f"{w_ns}vertAlign", {f"{w_ns}val": "sub"})
        if run.language:
            SubElement(r_pr, f"{w_ns}lang", {f"{w_ns}val": run.language})
        if run.rtl:
            SubElement(r_pr, f"{w_ns}rtl")
    if run.footnote_reference_id is not None:
        if r_pr is None:
            r_pr = SubElement(r, f"{w_ns}rPr")
        if not run.style:
            SubElement(r_pr, f"{w_ns}rStyle", {f"{w_ns}val": "FootnoteReference"})
        SubElement(r, f"{w_ns}footnoteReference", {f"{w_ns}id": str(run.footnote_reference_id)})
        return r
    if run.endnote_reference_id is not None:
        if r_pr is None:
            r_pr = SubElement(r, f"{w_ns}rPr")
        if not run.style:
            SubElement(r_pr, f"{w_ns}rStyle", {f"{w_ns}val": "EndnoteReference"})
        SubElement(r, f"{w_ns}endnoteReference", {f"{w_ns}id": str(run.endnote_reference_id)})
        return r
    if run.comment_reference_id is not None:
        if r_pr is None:
            r_pr = SubElement(r, f"{w_ns}rPr")
        if not run.style:
            SubElement(r_pr, f"{w_ns}rStyle", {f"{w_ns}val": "CommentReference"})
        SubElement(r, f"{w_ns}commentReference", {f"{w_ns}id": str(run.comment_reference_id)})
        return r
    if run.vertical and run.text:
        first = True
        for char in run.text:
            if char == "\n":
                SubElement(r, f"{w_ns}br")
                first = True
                continue
            if not first:
                SubElement(r, f"{w_ns}br")
            text = SubElement(r, f"{w_ns}t", {"xml:space": "preserve"})
            text.text = char
            first = False
        if not run.break_type:
            return r
    if run.break_type:
        attrs: dict[str, str] = {}
        if run.break_type in {"page", "column", "section"}:
            attrs[f"{w_ns}type"] = run.break_type
        SubElement(r, f"{w_ns}br", attrs)
        return r
    if run.text:
        text = SubElement(r, f"{w_ns}t", {"xml:space": "preserve"})
        text.text = run.text
    elif not run.break_type:
        SubElement(r, f"{w_ns}t", {"xml:space": "preserve"}).text = ""
    return r


def build_picture_paragraph(picture: Picture, relationships: RelationshipManager) -> Element:
    w_ns = f"{{{XML_NS['w']}}}"
    wp_ns = f"{{{XML_NS['wp']}}}"
    a_ns = f"{{{XML_NS['a']}}}"
    pic_ns = f"{{{XML_NS['pic']}}}"

    paragraph = Element(f"{w_ns}p")
    run = SubElement(paragraph, f"{w_ns}r")
    r_pr = SubElement(run, f"{w_ns}rPr")
    SubElement(r_pr, f"{w_ns}noProof")

    relationship_id, target = relationships.register_image(picture)
    cx = emus(picture.width)
    cy = emus(picture.height)

    drawing = SubElement(run, f"{w_ns}drawing")
    inline = SubElement(drawing, f"{wp_ns}inline")
    SubElement(inline, f"{wp_ns}extent", {"cx": str(cx), "cy": str(cy)})
    SubElement(inline, f"{wp_ns}effectExtent", {"l": "0", "t": "0", "r": "0", "b": "0"})
    doc_pr_attrs = {"id": "1", "name": picture.name or "Picture"}
    if picture.description:
        doc_pr_attrs["descr"] = picture.description
    SubElement(inline, f"{wp_ns}docPr", doc_pr_attrs)
    SubElement(inline, f"{wp_ns}cNvGraphicFramePr")

    graphic = SubElement(inline, f"{a_ns}graphic")
    graphic_data = SubElement(
        graphic,
        f"{a_ns}graphicData",
        {"uri": "http://schemas.openxmlformats.org/drawingml/2006/picture"},
    )
    pic = SubElement(graphic_data, f"{pic_ns}pic")
    nv_pic_pr = SubElement(pic, f"{pic_ns}nvPicPr")
    SubElement(nv_pic_pr, f"{pic_ns}cNvPr", {"id": "0", "name": picture.name or "Picture"})
    SubElement(nv_pic_pr, f"{pic_ns}cNvPicPr")

    blip_fill = SubElement(pic, f"{pic_ns}blipFill")
    SubElement(blip_fill, f"{a_ns}blip", {f"{{{XML_NS['r']}}}embed": relationship_id})
    stretch = SubElement(blip_fill, f"{a_ns}stretch")
    SubElement(stretch, f"{a_ns}fillRect")

    sp_pr = SubElement(pic, f"{pic_ns}spPr")
    xfrm = SubElement(sp_pr, f"{a_ns}xfrm")
    SubElement(xfrm, f"{a_ns}off", {"x": "0", "y": "0"})
    SubElement(xfrm, f"{a_ns}ext", {"cx": str(cx), "cy": str(cy)})
    prst_geom = SubElement(sp_pr, f"{a_ns}prstGeom", {"prst": "rect"})
    SubElement(prst_geom, f"{a_ns}avLst")

    return paragraph


def build_table_element(
    table: Table, relationships: RelationshipManager, bookmark_state: BookmarkState
) -> Element:
    w_ns = f"{{{XML_NS['w']}}}"
    tbl = Element(f"{w_ns}tbl")
    tbl_pr = SubElement(tbl, f"{w_ns}tblPr")
    SubElement(tbl_pr, f"{w_ns}tblStyle", {f"{w_ns}val": "TableGrid"})
    if table.alignment:
        SubElement(tbl_pr, f"{w_ns}jc", {f"{w_ns}val": table.alignment})
    if table.width:
        SubElement(
            tbl_pr,
            f"{w_ns}tblW",
            {f"{w_ns}type": "dxa", f"{w_ns}w": str(twips(table.width))},
        )
    if table.cell_padding is not None:
        cell_mar = SubElement(tbl_pr, f"{w_ns}tblCellMar")
        padding = str(twips(table.cell_padding))
        for side in ("top", "left", "bottom", "right"):
            SubElement(cell_mar, f"{w_ns}{side}", {f"{w_ns}type": "dxa", f"{w_ns}w": padding})
    if table.borders:
        tbl_borders = SubElement(tbl_pr, f"{w_ns}tblBorders")
        border_map = {
            "top": "top",
            "bottom": "bottom",
            "left": "left",
            "right": "right",
            "insideH": "insideH",
            "insideV": "insideV",
        }
        color = (table.border_color or "000000").replace("#", "").upper() or "auto"
        for key, xml_name in border_map.items():
            style = table.borders.get(key)
            if not style:
                continue
            SubElement(
                tbl_borders,
                f"{w_ns}{xml_name}",
                {
                    f"{w_ns}val": style,
                    f"{w_ns}sz": "4",
                    f"{w_ns}space": "0",
                    f"{w_ns}color": color,
                },
            )

    tbl_grid = SubElement(tbl, f"{w_ns}tblGrid")

    if table.column_widths:
        for width in table.column_widths:
            SubElement(tbl_grid, f"{w_ns}gridCol", {f"{w_ns}w": str(max(twips(width), 1))})
    elif table.rows and table.rows[0].cells:
        column_count = len(table.rows[0].cells)
        default_width = twips(table.width or 5000)
        col_width = max(default_width // max(column_count, 1), 1)
        for _ in range(column_count):
            SubElement(tbl_grid, f"{w_ns}gridCol", {f"{w_ns}w": str(col_width)})

    for row_index, row in enumerate(table.rows):
        tr = SubElement(tbl, f"{w_ns}tr")
        if row.is_header or (table.header_rows and row_index < table.header_rows):
            tr_pr = SubElement(tr, f"{w_ns}trPr")
            SubElement(tr_pr, f"{w_ns}tblHeader")
        for cell in row.cells:
            tc = SubElement(tr, f"{w_ns}tc")
            tc_pr = SubElement(tc, f"{w_ns}tcPr")
            SubElement(tc_pr, f"{w_ns}tcW", {f"{w_ns}type": "auto", f"{w_ns}w": "0"})
            if cell.row_span_continue:
                SubElement(tc_pr, f"{w_ns}vMerge")
            elif cell.row_span > 1:
                SubElement(tc_pr, f"{w_ns}vMerge", {f"{w_ns}val": "restart"})
            if cell.col_span > 1:
                SubElement(tc_pr, f"{w_ns}gridSpan", {f"{w_ns}val": str(cell.col_span)})
            if cell.background_color:
                fill = cell.background_color.replace("#", "").upper()
                SubElement(
                    tc_pr,
                    f"{w_ns}shd",
                    {f"{w_ns}val": "clear", f"{w_ns}color": "auto", f"{w_ns}fill": fill},
                )
            if cell.vertical_alignment:
                SubElement(tc_pr, f"{w_ns}vAlign", {f"{w_ns}val": cell.vertical_alignment})
            if cell.borders:
                tc_borders = SubElement(tc_pr, f"{w_ns}tcBorders")
                color = "auto"
                for side, style in cell.borders.items():
                    SubElement(
                        tc_borders,
                        f"{w_ns}{side}",
                        {
                            f"{w_ns}val": style,
                            f"{w_ns}sz": "4",
                            f"{w_ns}space": "0",
                            f"{w_ns}color": color,
                        },
                    )
            for element in cell.content:
                append_block(
                    tc,
                    _ensure_paragraph_alignment(element, cell),
                    relationships,
                    bookmark_state,
                )
    return tbl


def _ensure_paragraph_alignment(element: BlockElement, cell: TableCell) -> BlockElement:
    from ..ir import Paragraph as IRParagraph

    if not cell.alignment or not isinstance(element, IRParagraph):
        return element
    if element.alignment:
        return element
    clone = deepcopy(element)
    clone.alignment = cell.alignment
    return clone


def build_footnotes_xml(
    footnotes: Sequence[Footnote], relationships: RelationshipManager
) -> bytes:
    w_ns = f"{{{XML_NS['w']}}}"
    root = Element(f"{w_ns}footnotes")

    separator = SubElement(
        root,
        f"{w_ns}footnote",
        {f"{w_ns}type": "separator", f"{w_ns}id": "0"},
    )
    sep_p = SubElement(separator, f"{w_ns}p")
    sep_r = SubElement(sep_p, f"{w_ns}r")
    SubElement(sep_r, f"{w_ns}separator")

    continuation = SubElement(
        root,
        f"{w_ns}footnote",
        {f"{w_ns}type": "continuationSeparator", f"{w_ns}id": "1"},
    )
    cont_p = SubElement(continuation, f"{w_ns}p")
    cont_r = SubElement(cont_p, f"{w_ns}r")
    SubElement(cont_r, f"{w_ns}continuationSeparator")

    state = BookmarkState()
    for footnote in footnotes:
        attrs = {f"{w_ns}id": str(footnote.id)}
        footnote_el = SubElement(root, f"{w_ns}footnote", attrs)
        for paragraph in footnote.paragraphs:
            footnote_el.append(build_paragraph_element(paragraph, relationships, state))
    return serialize(root)


def build_endnotes_xml(
    endnotes: Sequence[Endnote], relationships: RelationshipManager
) -> bytes:
    w_ns = f"{{{XML_NS['w']}}}"
    root = Element(f"{w_ns}endnotes")

    separator = SubElement(
        root,
        f"{w_ns}endnote",
        {f"{w_ns}type": "separator", f"{w_ns}id": "0"},
    )
    sep_p = SubElement(separator, f"{w_ns}p")
    sep_r = SubElement(sep_p, f"{w_ns}r")
    SubElement(sep_r, f"{w_ns}separator")

    continuation = SubElement(
        root,
        f"{w_ns}endnote",
        {f"{w_ns}type": "continuationSeparator", f"{w_ns}id": "1"},
    )
    cont_p = SubElement(continuation, f"{w_ns}p")
    cont_r = SubElement(cont_p, f"{w_ns}r")
    SubElement(cont_r, f"{w_ns}continuationSeparator")

    state = BookmarkState()
    for endnote in endnotes:
        attrs = {f"{w_ns}id": str(endnote.id)}
        endnote_el = SubElement(root, f"{w_ns}endnote", attrs)
        for paragraph in endnote.paragraphs:
            endnote_el.append(build_paragraph_element(paragraph, relationships, state))
    return serialize(root)


def build_comments_xml(
    comments: Sequence[Comment], relationships: RelationshipManager
) -> bytes:
    w_ns = f"{{{XML_NS['w']}}}"
    root = Element(f"{w_ns}comments")
    state = BookmarkState()
    for comment in comments:
        attrs = {f"{w_ns}id": str(comment.id)}
        if comment.author:
            attrs[f"{w_ns}author"] = comment.author
        comment_el = SubElement(root, f"{w_ns}comment", attrs)
        for paragraph in comment.paragraphs:
            comment_el.append(build_paragraph_element(paragraph, relationships, state))
    return serialize(root)


def append_block(
    parent: Element,
    element: BlockElement,
    relationships: RelationshipManager,
    bookmark_state: BookmarkState,
) -> None:
    from ..ir import Paragraph as IRParagraph  # local import to avoid cycle
    from ..ir import Picture as IRPicture
    from ..ir import Table as IRTable

    if isinstance(element, IRParagraph):
        parent.append(build_paragraph_element(element, relationships, bookmark_state))
    elif isinstance(element, IRPicture):
        parent.append(build_picture_paragraph(element, relationships))
    elif isinstance(element, IRTable):
        parent.append(build_table_element(element, relationships, bookmark_state))
    elif isinstance(element, Equation):
        parent.append(build_equation_paragraph(element, relationships, bookmark_state))
    elif isinstance(element, Annotation):
        parent.append(build_paragraph_element(element.as_paragraph(), relationships, bookmark_state))
    elif isinstance(element, Shape):
        parent.append(build_paragraph_element(element.as_paragraph(), relationships, bookmark_state))
    else:
        raise TypeError(f"Unsupported block element: {type(element)!r}")


def build_header_footer_xml(
    container: HeaderFooter,
    relationships: RelationshipManager,
    kind: str,
    bookmark_state: BookmarkState | None = None,
) -> bytes:
    w_ns = f"{{{XML_NS['w']}}}"
    tag = "hdr" if kind == "header" else "ftr"
    root = Element(f"{w_ns}{tag}")
    state = bookmark_state or BookmarkState()
    for element in container.content:
        append_block(root, element, relationships, state)
    if container.metadata and container.metadata.get("page_numbers") == "true":
        p = SubElement(root, f"{w_ns}p")
        fld_page = SubElement(p, f"{w_ns}fldSimple", {f"{w_ns}instr": " PAGE "})
        r_page = SubElement(fld_page, f"{w_ns}r")
        SubElement(r_page, f"{w_ns}t").text = "1"
        text_run = SubElement(p, f"{w_ns}r")
        SubElement(text_run, f"{w_ns}t").text = " of "
        fld_total = SubElement(p, f"{w_ns}fldSimple", {f"{w_ns}instr": " NUMPAGES "})
        r_total = SubElement(fld_total, f"{w_ns}r")
        SubElement(r_total, f"{w_ns}t").text = "1"
    if not list(root):
        SubElement(root, f"{w_ns}p")
    return serialize(root)


def build_section_properties(section: Section, relationships: RelationshipManager, index: int) -> Element:
    w_ns = f"{{{XML_NS['w']}}}"
    r_ns = f"{{{XML_NS['r']}}}"
    sect_pr = Element(f"{w_ns}sectPr")
    pg_sz_attrs = {f"{w_ns}w": str(twips(section.page_width)), f"{w_ns}h": str(twips(section.page_height))}
    if section.orientation.lower() == "landscape":
        pg_sz_attrs[f"{w_ns}orient"] = "landscape"
    SubElement(sect_pr, f"{w_ns}pgSz", pg_sz_attrs)
    SubElement(
        sect_pr,
        f"{w_ns}pgMar",
        {
            f"{w_ns}top": str(twips(section.margin_top)),
            f"{w_ns}bottom": str(twips(section.margin_bottom)),
            f"{w_ns}left": str(twips(section.margin_left)),
            f"{w_ns}right": str(twips(section.margin_right)),
            f"{w_ns}header": str(twips(36)),
            f"{w_ns}footer": str(twips(36)),
            f"{w_ns}gutter": "0",
        },
    )
    if section.columns > 1:
        space = section.column_spacing if section.column_spacing is not None else 18.0
        SubElement(
            sect_pr,
            f"{w_ns}cols",
            {f"{w_ns}num": str(section.columns), f"{w_ns}space": str(twips(space))},
        )
    has_first_page = bool((section.first_page_header and section.first_page_header.content) or (section.first_page_footer and section.first_page_footer.content))
    if has_first_page:
        SubElement(sect_pr, f"{w_ns}titlePg")
    if section.header and section.header.content:
        header_xml = build_header_footer_xml(
            section.header, relationships, "header", BookmarkState()
        )
        part_name = f"header{index + 1}.xml"
        rid = relationships.register_part(
            part_name=part_name,
            data=header_xml,
            relationship_type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml",
        )
        SubElement(sect_pr, f"{w_ns}headerReference", {f"{w_ns}type": "default", f"{r_ns}id": rid})
    if section.first_page_header and section.first_page_header.content:
        header_first_xml = build_header_footer_xml(
            section.first_page_header, relationships, "header", BookmarkState()
        )
        part_name = f"header{index + 1}_first.xml"
        rid = relationships.register_part(
            part_name=part_name,
            data=header_first_xml,
            relationship_type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml",
        )
        SubElement(sect_pr, f"{w_ns}headerReference", {f"{w_ns}type": "first", f"{r_ns}id": rid})
    if section.footer and section.footer.content:
        footer_xml = build_header_footer_xml(
            section.footer, relationships, "footer", BookmarkState()
        )
        part_name = f"footer{index + 1}.xml"
        rid = relationships.register_part(
            part_name=part_name,
            data=footer_xml,
            relationship_type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml",
        )
        SubElement(sect_pr, f"{w_ns}footerReference", {f"{w_ns}type": "default", f"{r_ns}id": rid})
    if section.first_page_footer and section.first_page_footer.content:
        footer_first_xml = build_header_footer_xml(
            section.first_page_footer, relationships, "footer", BookmarkState()
        )
        part_name = f"footer{index + 1}_first.xml"
        rid = relationships.register_part(
            part_name=part_name,
            data=footer_first_xml,
            relationship_type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml",
        )
        SubElement(sect_pr, f"{w_ns}footerReference", {f"{w_ns}type": "first", f"{r_ns}id": rid})
    return sect_pr


def build_document_xml(document: Document, relationships: RelationshipManager) -> bytes:
    w_ns = f"{{{XML_NS['w']}}}"
    root = Element(f"{w_ns}document")
    body = SubElement(root, f"{w_ns}body")

    sections = list(document.iter_sections())
    bookmark_state = BookmarkState()
    for index, section in enumerate(sections):
        for element in section.iter_elements():
            append_block(body, element, relationships, bookmark_state)
        sect_pr = build_section_properties(section, relationships, index)
        if index == len(sections) - 1:
            body.append(sect_pr)
        else:
            p = SubElement(body, f"{w_ns}p")
            p_pr = SubElement(p, f"{w_ns}pPr")
            p_pr.append(sect_pr)
    return serialize(root)


def build_equation_paragraph(
    equation: Equation,
    relationships: RelationshipManager,
    bookmark_state: BookmarkState,
) -> Element:
    w_ns = f"{{{XML_NS['w']}}}"
    m_ns = f"{{{XML_NS['m']}}}"

    def _append_alt_text(container: Element) -> None:
        if not equation.description:
            return
        alt_run = Element(f"{w_ns}r")
        r_pr = SubElement(alt_run, f"{w_ns}rPr")
        SubElement(r_pr, f"{w_ns}vanish")
        text = SubElement(alt_run, f"{w_ns}t", {"xml:space": "preserve"})
        text.text = equation.description
        container.append(alt_run)

    if equation.omml:
        paragraph = Element(f"{w_ns}p")
        _append_alt_text(paragraph)
        try:
            math_element = fromstring(equation.omml)
        except ParseError:
            math_element = None
        if math_element is not None:
            if math_element.tag == f"{m_ns}oMathPara":
                paragraph.append(math_element)
            else:
                if math_element.tag != f"{m_ns}oMath":
                    wrapper = Element(f"{m_ns}oMath")
                    wrapper.append(math_element)
                    math_element = wrapper
                math_para = Element(f"{m_ns}oMathPara")
                math_para.append(math_element)
                paragraph.append(math_para)
            return paragraph

    if equation.picture is not None:
        picture_paragraph = build_picture_paragraph(equation.picture, relationships)
        if equation.description:
            hidden = Element(f"{w_ns}r")
            r_pr = SubElement(hidden, f"{w_ns}rPr")
            SubElement(r_pr, f"{w_ns}vanish")
            text = SubElement(hidden, f"{w_ns}t", {"xml:space": "preserve"})
            text.text = equation.description
            picture_paragraph.insert(0, hidden)
        return picture_paragraph

    paragraph = Element(f"{w_ns}p")
    _append_alt_text(paragraph)
    content = equation.text or equation.description or "Equation"
    run = SubElement(paragraph, f"{w_ns}r")
    text = SubElement(run, f"{w_ns}t", {"xml:space": "preserve"})
    text.text = content
    return paragraph
