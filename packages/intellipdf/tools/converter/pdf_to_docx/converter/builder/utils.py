"""Utility helpers shared across the document builder modules."""

from __future__ import annotations

from statistics import fmean
from typing import Iterable, Iterator

from ...ir import Paragraph, Run, Section
from ...primitives import BoundingBox, OutlineNode, Page, TextBlock


def bbox_overlap_ratio(block: TextBlock, link_bbox: BoundingBox) -> float:
    """Return the area overlap ratio between a text block and link bounding box."""

    block_bbox = block.bbox
    inter_left = max(block_bbox.left, link_bbox.left)
    inter_right = min(block_bbox.right, link_bbox.right)
    inter_bottom = max(block_bbox.bottom, link_bbox.bottom)
    inter_top = min(block_bbox.top, link_bbox.top)
    width = max(0.0, inter_right - inter_left)
    height = max(0.0, inter_top - inter_bottom)
    if width <= 0.0 or height <= 0.0:
        return 0.0
    intersection = width * height
    block_area = max(
        1.0,
        (block_bbox.right - block_bbox.left) * (block_bbox.top - block_bbox.bottom),
    )
    return intersection / block_area


def bbox_intersection_ratio(a: BoundingBox, b: BoundingBox) -> float:
    inter_left = max(a.left, b.left)
    inter_right = min(a.right, b.right)
    inter_bottom = max(a.bottom, b.bottom)
    inter_top = min(a.top, b.top)
    width = max(0.0, inter_right - inter_left)
    height = max(0.0, inter_top - inter_bottom)
    if width <= 0.0 or height <= 0.0:
        return 0.0
    intersection = width * height
    area = max(1.0, (a.right - a.left) * (a.top - a.bottom))
    return intersection / area


def estimate_margins(page: Page) -> tuple[float, float, float, float]:
    lefts: list[float] = []
    rights: list[float] = []
    tops: list[float] = []
    bottoms: list[float] = []

    for block in page.text_blocks:
        if block.text.strip():
            lefts.append(block.bbox.left)
            rights.append(block.bbox.right)
            tops.append(block.bbox.top)
            bottoms.append(block.bbox.bottom)
    for image in page.images:
        lefts.append(image.bbox.left)
        rights.append(image.bbox.right)
        tops.append(image.bbox.top)
        bottoms.append(image.bbox.bottom)

    if not lefts or not rights or not tops or not bottoms:
        return (72.0, 72.0, 72.0, 72.0)

    width = max(page.width, 1.0)
    height = max(page.height, 1.0)

    margin_left = max(12.0, min(lefts))
    margin_right = max(12.0, width - max(rights))
    margin_bottom = max(12.0, min(bottoms))
    margin_top = max(12.0, height - max(tops))

    margin_left = min(margin_left, width / 2)
    margin_right = min(margin_right, width / 2)
    margin_top = min(margin_top, height / 2)
    margin_bottom = min(margin_bottom, height / 2)

    # Clamp extreme margins to reasonable maximum (approx 2.5 inches)
    max_margin = 180.0
    margin_top = min(margin_top, max_margin)
    margin_bottom = min(margin_bottom, max_margin)
    margin_left = min(margin_left, max_margin)
    margin_right = min(margin_right, max_margin)

    return (margin_top, margin_bottom, margin_left, margin_right)


def column_index(block: TextBlock, section: Section) -> int | None:
    if section.columns <= 1:
        return None
    usable_width = section.page_width - section.margin_left - section.margin_right
    if usable_width <= 0:
        return None
    spacing = section.column_spacing if section.column_spacing is not None else 18.0
    spacing = max(spacing, 0.0)
    columns = max(section.columns, 1)
    total_spacing = spacing * (columns - 1)
    column_width = (usable_width - total_spacing) / columns if columns else usable_width
    if column_width <= 0:
        column_width = usable_width / columns if columns else usable_width
    relative_left = max(0.0, block.bbox.left - section.margin_left)
    current_edge = 0.0
    for index in range(columns):
        upper_bound = current_edge + column_width
        if relative_left <= upper_bound + 0.1:
            return max(0, min(index, columns - 1))
        current_edge += column_width + spacing
    return columns - 1


def same_geometry(
    section: Section,
    page: Page,
    margins: tuple[float, float, float, float],
    columns: int,
    spacing: float | None,
    orientation: str,
    tolerance: float = 0.5,
) -> bool:
    margin_top, margin_bottom, margin_left, margin_right = margins
    if abs(section.page_width - page.width) > tolerance:
        return False
    if abs(section.page_height - page.height) > tolerance:
        return False
    margin_tolerance = 6.0
    if abs(section.margin_top - margin_top) > margin_tolerance:
        return False
    if abs(section.margin_bottom - margin_bottom) > margin_tolerance:
        return False
    if abs(section.margin_left - margin_left) > margin_tolerance:
        return False
    if abs(section.margin_right - margin_right) > margin_tolerance:
        return False
    if section.columns != columns:
        return False
    spacing_tolerance = 3.0
    if (section.column_spacing is None) != (spacing is None):
        return False
    if (
        section.column_spacing is not None
        and spacing is not None
        and abs(section.column_spacing - spacing) > spacing_tolerance
    ):
        return False
    if section.orientation.lower() != orientation.lower():
        return False
    return True


def paragraph_bbox(paragraph: Paragraph) -> BoundingBox | None:
    metadata = paragraph.metadata or {}
    try:
        left = float(metadata.get("bbox_left"))
        right = float(metadata.get("bbox_right"))
        top = float(metadata.get("bbox_top"))
        bottom = float(metadata.get("bbox_bottom"))
    except (TypeError, ValueError, KeyError):
        return None
    return BoundingBox(left=left, bottom=bottom, right=right, top=top)


def paragraph_covers_position(
    paragraph: Paragraph,
    page_number: int,
    top: float | None,
    *,
    tolerance_ratio: float = 0.25,
    fallback_tolerance: float = 12.0,
) -> bool:
    metadata = paragraph.metadata or {}
    try:
        start = int(metadata.get("start_page", page_number))
        end = int(metadata.get("end_page", start))
    except (TypeError, ValueError):
        start = end = page_number
    if page_number < start or page_number > end:
        return False
    if top is None:
        return True
    try:
        bbox_top = float(metadata.get("bbox_top"))
        bbox_bottom = float(metadata.get("bbox_bottom"))
    except (TypeError, ValueError):
        return False
    tolerance = max((bbox_top - bbox_bottom) * tolerance_ratio, fallback_tolerance)
    return (bbox_bottom - tolerance) <= top <= (bbox_top + tolerance)


def average_font_size(paragraph: Paragraph) -> float | None:
    sizes = [run.font_size for run in paragraph.runs if run.font_size]
    if not sizes:
        return None
    return fmean(sizes)


def block_matches_position(block: TextBlock, top: float) -> bool:
    tolerance = max(block.font_size or 12.0, (block.bbox.top - block.bbox.bottom) * 0.25)
    return (block.bbox.bottom - tolerance) <= top <= (block.bbox.top + tolerance)


def comment_paragraphs_from_text(text: str) -> list[Paragraph]:
    lines = text.splitlines() or [text]
    paragraphs: list[Paragraph] = []
    for line in lines:
        paragraphs.append(Paragraph(runs=[Run(text=line.strip())]))
    if not paragraphs:
        paragraphs.append(Paragraph(runs=[Run(text="")]))
    return paragraphs


def iter_outline_nodes(nodes: Iterable[OutlineNode]) -> Iterator[OutlineNode]:
    for node in nodes:
        yield node
        if node.children:
            yield from iter_outline_nodes(node.children)
