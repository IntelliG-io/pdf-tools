"""Footnote and comment handling helpers for the document builder."""

from __future__ import annotations

import re
from statistics import fmean

from ...ir import Comment, Endnote, Footnote, Paragraph, Run
from ...primitives import PdfAnnotation, TextBlock
from .utils import (
    bbox_intersection_ratio,
    comment_paragraphs_from_text,
    paragraph_bbox,
)

if False:  # pragma: no cover
    from .document import DocumentBuilder


def record_superscript_marker(
    builder: "DocumentBuilder", run: Run, block: TextBlock, page_number: int | None
) -> None:
    if not block.superscript:
        return
    marker = normalise_marker_text(block.text)
    if marker is None:
        return
    paragraph = builder._pending_paragraph
    if paragraph is None:
        return
    page = page_number
    if page is None:
        page = (
            builder._current_page_number
            if builder._current_page_number is not None
            else builder._previous_page_number
        )
    if page is None:
        return
    builder._footnote_markers_by_page[page].append((marker, paragraph, run))


def normalise_marker_text(text: str | None) -> str | None:
    if not text:
        return None
    cleaned = re.sub(r"[^0-9A-Za-z\*\u2020\u2021]", "", text)
    if not cleaned:
        return None
    cleaned = cleaned.lower()
    if cleaned.isdigit():
        return cleaned
    if cleaned in {"*", "†", "‡"}:
        return cleaned
    if len(cleaned) == 1 and cleaned.isalpha():
        return cleaned
    return None


def process_comments(builder: "DocumentBuilder", document) -> None:
    builder._comments.clear()
    comment_id = 0
    for page in sorted(builder._annotations_by_page):
        annotations = builder._annotations_by_page[page]
        if not annotations:
            continue
        for annotation in annotations:
            text = (annotation.text or "").strip()
            if not text:
                continue
            target = _paragraph_for_annotation(builder, page, annotation)
            if target is None:
                continue
            comment_paragraphs = comment_paragraphs_from_text(annotation.text or "")
            comment = Comment(
                id=comment_id,
                paragraphs=comment_paragraphs,
                author=annotation.author,
                text=annotation.text,
                page_number=page,
            )
            _attach_comment_to_paragraph(target, comment_id)
            builder._comments.append(comment)
            comment_id += 1


def process_footnotes(builder: "DocumentBuilder", document) -> None:
    builder._footnotes.clear()
    builder._endnotes.clear()
    next_id = 2  # Reserve 0 and 1 for built-in separators
    for page in sorted(builder._page_elements):
        section = builder._page_section_map.get(page)
        if section is None:
            continue
        elements = builder._page_elements.get(page)
        if not elements:
            continue
        seen: set[int] = set()
        for element in list(elements):
            if not isinstance(element, Paragraph):
                continue
            if id(element) in seen:
                continue
            seen.add(id(element))
            candidate = _footnote_candidate_info(builder, element, page, section)
            if candidate is None:
                continue
            marker, prefix_length = candidate
            reference = _find_marker_run(builder, page, marker)
            if reference is None:
                reference = _find_marker_run(builder, page - 1, marker)
            if reference is None:
                continue
            _, run = reference
            footnote_id = next_id
            next_id += 1
            note_type = "endnote" if builder._footnotes_as_endnotes else "footnote"
            _convert_run_to_note_reference(run, footnote_id, note_type)
            _strip_paragraph_prefix(element, prefix_length)
            for section_obj in document.sections:
                if element in section_obj.elements:
                    section_obj.elements.remove(element)
                    break
            for page_list in builder._page_elements.values():
                while element in page_list:
                    page_list.remove(element)
            if builder._footnotes_as_endnotes:
                builder._endnotes.append(
                    Endnote(
                        id=footnote_id,
                        paragraphs=[element],
                        page_number=page,
                        marker=marker,
                    )
                )
            else:
                builder._footnotes.append(
                    Footnote(
                        id=footnote_id,
                        paragraphs=[element],
                        page_number=page,
                        marker=marker,
                    )
                )


def _paragraph_for_annotation(
    builder: "DocumentBuilder", page: int, annotation: PdfAnnotation
) -> Paragraph | None:
    elements = builder._page_elements.get(page)
    if not elements:
        return None
    best_score = 0.0
    best_paragraph: Paragraph | None = None
    seen: set[int] = set()
    for element in elements:
        if not isinstance(element, Paragraph):
            continue
        if id(element) in seen:
            continue
        seen.add(id(element))
        bbox = paragraph_bbox(element)
        if bbox is None:
            continue
        score = bbox_intersection_ratio(bbox, annotation.bbox)
        if score <= 0.1:
            continue
        if score > best_score:
            best_score = score
            best_paragraph = element
    return best_paragraph


def _attach_comment_to_paragraph(paragraph: Paragraph, comment_id: int) -> None:
    if not paragraph.runs:
        paragraph.runs.append(Run(text=""))
    first_run = paragraph.runs[0]
    if comment_id not in first_run.comment_range_start_ids:
        first_run.comment_range_start_ids.append(comment_id)
    last_run = paragraph.runs[-1]
    if comment_id not in last_run.comment_range_end_ids:
        last_run.comment_range_end_ids.append(comment_id)
    paragraph.runs.append(
        Run(text="", comment_reference_id=comment_id, style="CommentReference")
    )


def _footnote_candidate_info(
    builder: "DocumentBuilder", paragraph: Paragraph, page: int, section
) -> tuple[str, int] | None:
    metadata = paragraph.metadata or {}
    if metadata.get("generated"):
        return None
    if paragraph.numbering is not None:
        return None
    try:
        top = float(metadata.get("bbox_top"))
        bottom = float(metadata.get("bbox_bottom"))
    except (TypeError, ValueError, KeyError):
        return None
    page_height = builder._page_dimensions.get(page, (section.page_width, section.page_height))[1]
    threshold = section.margin_bottom + max(72.0, page_height * 0.15)
    if top > threshold:
        return None
    sizes = [run.font_size for run in paragraph.runs if run.font_size]
    if sizes and fmean(sizes) > 12.5:
        return None
    text = paragraph.text()
    match = re.match(r"^\s*([0-9A-Za-z]{1,3}|[\*\u2020\u2021])(?:[\.\)]|\s)+", text)
    if not match:
        return None
    marker = normalise_marker_text(match.group(1))
    if marker is None:
        return None
    prefix_length = match.end()
    if prefix_length >= len(text):
        return None
    if (top - bottom) <= 0:
        return None
    return marker, prefix_length


def _find_marker_run(
    builder: "DocumentBuilder", page: int, marker: str
) -> tuple[Paragraph, Run] | None:
    entries = builder._footnote_markers_by_page.get(page)
    if not entries:
        return None
    for index, (candidate, paragraph, run) in enumerate(entries):
        if candidate == marker:
            entries.pop(index)
            return paragraph, run
    return None


def _convert_run_to_note_reference(run: Run, note_id: int, note_type: str) -> None:
    run.text = ""
    run.superscript = False
    run.subscript = False
    if note_type == "endnote":
        run.style = "EndnoteReference"
        run.footnote_reference_id = None
        run.endnote_reference_id = note_id
    else:
        run.style = "FootnoteReference"
        run.footnote_reference_id = note_id
        run.endnote_reference_id = None


def _strip_paragraph_prefix(paragraph: Paragraph, length: int) -> None:
    remaining = length
    for run in paragraph.runs:
        text = run.text or ""
        if not text:
            continue
        if remaining <= 0:
            break
        if len(text) <= remaining:
            run.text = ""
            remaining -= len(text)
        else:
            run.text = text[remaining:]
            remaining = 0
            break
    for run in paragraph.runs:
        if run.text:
            trimmed = run.text.lstrip()
            if trimmed != run.text:
                run.text = trimmed
            break
    paragraph.runs = [
        r
        for r in paragraph.runs
        if r.text or r.break_type or r.footnote_reference_id or r.comment_reference_id
    ]
