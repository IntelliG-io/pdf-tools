"""Layout grouping helpers for the converter."""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import dataclass, field
import re
from statistics import fmean
from typing import Iterable, Mapping, Sequence

from ..ir import (
    Annotation,
    BlockElement,
    HeaderFooter,
    Numbering,
    Paragraph,
    Picture,
    Run,
    Section,
    Table,
    TableCell,
    TableRow,
)
from ..primitives import BoundingBox, Line, Page, Path, TextBlock
from .constants import ANNOTATION_ROLES
from .forms import form_field_to_table
from .images import image_to_picture, line_to_picture, path_to_picture
from .math import block_is_equation, block_to_equation
from .lists import normalise_text_for_numbering
from .text import font_traits, normalise_text_content

__all__ = [
    "assign_headers_footers",
    "blocks_can_merge",
    "blocks_to_paragraphs_static",
    "collect_page_placements",
    "detect_tables",
    "infer_alignment",
    "infer_columns",
    "infer_style",
]

_HEADER_ROLES = {"TH", "THEAD", "HEADER", "TABLEHEADER"}
_CELL_ROLES = {"TD", "TH", "CELL", "TABLECELL", "HEADER", "DATA"}
_DEFAULT_HEADER_FILL = "D9D9D9"
_REGION_TOLERANCE = 24.0
_MAX_REGION_PARAGRAPHS = 3
_DIGIT_RE = re.compile(r"\d+")
_SPACE_RE = re.compile(r"\s+")


@dataclass(slots=True)
class TableDetection:
    bbox: BoundingBox
    table: Table
    used_blocks: set[int] = field(default_factory=set)
    used_lines: set[int] = field(default_factory=set)


@dataclass(slots=True)
class CellData:
    blocks: list[int] = field(default_factory=list)
    row_span: int = 1
    col_span: int = 1
    header: bool = False
    background: str | None = None
    alignment: str | None = None
    vertical_alignment: str | None = None


@dataclass(slots=True)
class _RegionCandidate:
    page: int
    paragraphs: list[Paragraph] = field(default_factory=list)
    signature: tuple[str, ...] = ()


def _rgb_tuple_to_hex(color: tuple[float, float, float]) -> str:
    r = int(round(max(0.0, min(color[0], 1.0)) * 255))
    g = int(round(max(0.0, min(color[1], 1.0)) * 255))
    b = int(round(max(0.0, min(color[2], 1.0)) * 255))
    return f"{r:02X}{g:02X}{b:02X}"


def _bbox_contains(outer: BoundingBox, inner: BoundingBox, tolerance: float = 2.0) -> bool:
    return (
        inner.left >= outer.left - tolerance
        and inner.right <= outer.right + tolerance
        and inner.bottom >= outer.bottom - tolerance
        and inner.top <= outer.top + tolerance
    )


def _apply_path_backgrounds(page: Page) -> set[int]:
    used: set[int] = set()
    if not getattr(page, "paths", None):
        return used
    for index, path in enumerate(page.paths):
        if not path.is_rectangle:
            continue
        if path.fill_color is None or path.fill_alpha <= 0.1:
            continue
        bbox = path.bbox
        fill_hex = _rgb_tuple_to_hex(path.fill_color)
        matched = False
        for block in page.text_blocks:
            if not block.text:
                continue
            if _bbox_contains(bbox, block.bbox, tolerance=4.0):
                if not block.background_color:
                    block.background_color = fill_hex
                if path.fill_alpha < 1.0:
                    block.opacity = block.opacity or path.fill_alpha
                matched = True
        if matched:
            used.add(index)
    return used


def infer_alignment(block: TextBlock, section: Section) -> str | None:
    usable_width = section.page_width - section.margin_left - section.margin_right
    if usable_width <= 0:
        return None
    width = max(block.bbox.right - block.bbox.left, 1.0)
    center = (block.bbox.left + block.bbox.right) / 2
    page_center = section.margin_left + usable_width / 2
    if abs(center - page_center) <= max(10.0, width * 0.1):
        return "center"
    right_edge = section.page_width - section.margin_right
    if block.bbox.right >= right_edge - 5.0 and block.bbox.left > section.margin_left + width * 0.25:
        return "right"
    if width >= usable_width * 0.9:
        return "both"
    return "left"


def infer_style(block: TextBlock, numbering: Numbering | None, font_samples: Sequence[float]) -> str | None:
    if numbering is not None:
        return "ListParagraph"
    if block.role:
        role = block.role.upper()
        if role.startswith("H") and role[1:].isdigit():
            return f"Heading{role[1:]}"
        if role in {"TITLE", "SUBTITLE"}:
            return "Title" if role == "TITLE" else "Subtitle"
        if role in {"QUOTE", "BLOCKQUOTE"}:
            return "Quote"
        if role in {"CODE", "PRE"}:
            return "Code"
        if role in {"CAPTION"}:
            return "Caption"
    if not block.font_size:
        return None
    baseline = fmean(font_samples) if font_samples else block.font_size
    if baseline <= 0:
        return None
    ratio = block.font_size / baseline
    if ratio >= 1.8:
        return "Heading1"
    if ratio >= 1.5:
        return "Heading2"
    if ratio >= 1.3:
        return "Heading3"
    return None


def blocks_can_merge(previous: TextBlock | None, current: TextBlock) -> bool:
    if previous is None:
        return False
    if previous.vertical or current.vertical:
        return False
    if previous.role and current.role and previous.role != current.role:
        return False
    baseline = current.font_size or previous.font_size or 12.0
    vertical_gap = previous.bbox.bottom - current.bbox.top
    return vertical_gap <= baseline * 1.2


def blocks_to_paragraphs_static(
    blocks: Sequence[TextBlock],
    strip_whitespace: bool,
    alignment: str | None = None,
) -> list[Paragraph]:
    paragraphs: list[Paragraph] = []
    previous: TextBlock | None = None
    for block in sorted(blocks, key=lambda blk: (-blk.bbox.top, blk.bbox.left)):
        text = normalise_text_content(block.text, strip=strip_whitespace)
        if not text:
            previous = block
            continue
        working_block = deepcopy(block)
        working_block.text = text
        content, numbering = normalise_text_for_numbering(working_block, None)
        if not paragraphs or not blocks_can_merge(previous, block):
            bold, italic, underline = font_traits(block.font_name)
            run = Run(
                text=content,
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
            paragraphs.append(
                Paragraph(
                    runs=[run],
                    role=block.role,
                    numbering=numbering,
                    bidi=block.rtl,
                    alignment=alignment,
                )
            )
        else:
            paragraph = paragraphs[-1]
            last_run = paragraph.runs[-1]
            if (
                not block.vertical
                and not last_run.vertical
                and last_run.text
                and not last_run.text.endswith(" ")
                and not content.startswith(" ")
            ):
                last_run.text += " "
            bold, italic, underline = font_traits(block.font_name)
            paragraph.runs.append(
                Run(
                    text=content,
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
            paragraph.bidi = paragraph.bidi or block.rtl
            if alignment and not paragraph.alignment:
                paragraph.alignment = alignment
        previous = block
    return paragraphs


def collect_page_placements(page: Page, strip_whitespace: bool) -> list[tuple[float, float, str, object]]:
    placements: list[tuple[float, float, str, object]] = []
    background_paths = _apply_path_backgrounds(page)
    tables, used_blocks, used_lines = detect_tables(page, strip_whitespace)
    used_images: set[int] = set()
    available_lines = [
        line for index, line in enumerate(page.lines) if index not in used_lines
    ]
    for bbox, table in tables:
        placements.append((bbox.top, bbox.left, "table", table))
    for field in getattr(page, "form_fields", []):
        table = form_field_to_table(field, strip_whitespace=strip_whitespace)
        placements.append((field.bbox.top, field.bbox.left, "table", table))
    for index, block in enumerate(page.text_blocks):
        if index in used_blocks:
            continue
        if block_is_equation(block):
            detection = block_to_equation(block, page.images, used_images, available_lines)
            if detection.used_image_index is not None:
                used_images.add(detection.used_image_index)
            placements.append(
                (block.bbox.top, block.bbox.left, "equation", detection.equation)
            )
            used_blocks.add(index)
            continue
        if block.role and block.role.upper() in ANNOTATION_ROLES:
            text = block.text.strip() if strip_whitespace else block.text
            placements.append((block.bbox.top, block.bbox.left, "annotation", Annotation(text=text, kind=block.role)))
            used_blocks.add(index)
    for image_index, img in enumerate(page.images):
        if image_index in used_images:
            continue
        picture = image_to_picture(img)
        placements.append((img.bbox.top, img.bbox.left, "picture", picture))
    for index, line in enumerate(page.lines):
        if index in used_lines:
            continue
        bbox = BoundingBox(
            left=min(line.start[0], line.end[0]),
            bottom=min(line.start[1], line.end[1]),
            right=max(line.start[0], line.end[0]),
            top=max(line.start[1], line.end[1]),
        )
        picture = line_to_picture(line)
        placements.append((bbox.top, bbox.left, "picture", picture))
    for index, path in enumerate(page.paths):
        if index in background_paths:
            continue
        bbox = path.bbox
        picture = path_to_picture(path)
        placements.append((bbox.top, bbox.left, "picture", picture))
    for index, block in enumerate(page.text_blocks):
        if index in used_blocks:
            continue
        placements.append((block.bbox.top, block.bbox.left, "text", block))
    placements.sort(key=lambda item: (-item[0], item[1], 0 if item[2] == "text" else 1))
    return placements


def detect_tables(page: Page, strip_whitespace: bool) -> tuple[list[tuple[BoundingBox, Table]], set[int], set[int]]:
    detections: list[TableDetection] = []
    used_blocks: set[int] = set()
    used_lines: set[int] = set()

    for detection in _detect_tables_from_tagged(page, strip_whitespace, used_blocks):
        detections.append(detection)
        used_blocks.update(detection.used_blocks)
        used_lines.update(detection.used_lines)

    for detection in _detect_tables_from_lines(page, strip_whitespace, used_blocks):
        detections.append(detection)
        used_blocks.update(detection.used_blocks)
        used_lines.update(detection.used_lines)

    for detection in _detect_tables_from_whitespace(page, strip_whitespace, used_blocks):
        detections.append(detection)
        used_blocks.update(detection.used_blocks)
        used_lines.update(detection.used_lines)

    tables = [(detection.bbox, detection.table) for detection in detections]
    return tables, used_blocks, used_lines


def _detect_tables_from_tagged(
    page: Page,
    strip_whitespace: bool,
    used_blocks: set[int],
) -> Iterable[TableDetection]:
    candidates = [
        index
        for index, block in enumerate(page.text_blocks)
        if index not in used_blocks and (block.role or "").upper() in _CELL_ROLES
    ]
    if not candidates:
        return []

    detections: list[TableDetection] = []
    for cluster in _cluster_indices_by_bbox(candidates, page, tolerance=12.0):
        cluster = [index for index in cluster if index not in used_blocks]
        if len(cluster) < 4:
            continue
        row_edges = _grid_edges_from_centers(page, cluster, vertical=True)
        column_edges = _grid_edges_from_centers(page, cluster, vertical=False)
        if len(row_edges) < 2 or len(column_edges) < 2:
            continue
        detection = _build_table_from_grid(
            page,
            cluster,
            row_edges,
            column_edges,
            strip_whitespace,
            borders={
                "top": "single",
                "bottom": "single",
                "left": "single",
                "right": "single",
                "insideH": "single",
                "insideV": "single",
            },
            border_color="000000",
            cell_padding=3.0,
        )
        if detection:
            detections.append(detection)
    return detections


def _detect_tables_from_lines(
    page: Page,
    strip_whitespace: bool,
    used_blocks: set[int],
) -> Iterable[TableDetection]:
    horizontals: list[tuple[int, Line]] = []
    verticals: list[tuple[int, Line]] = []
    for index, line in enumerate(page.lines):
        if abs(line.start[1] - line.end[1]) <= 0.5:
            horizontals.append((index, line))
        elif abs(line.start[0] - line.end[0]) <= 0.5:
            verticals.append((index, line))
    if len(horizontals) < 2 or len(verticals) < 2:
        return []

    y_values = sorted(
        {line.start[1] for _, line in horizontals} | {line.end[1] for _, line in horizontals},
        reverse=True,
    )
    x_values = sorted({line.start[0] for _, line in verticals} | {line.end[0] for _, line in verticals})
    row_edges = _cluster_positions(y_values, tolerance=1.0, reverse=True)
    column_edges = _cluster_positions(x_values, tolerance=1.0, reverse=False)
    if len(row_edges) < 2 or len(column_edges) < 2:
        return []

    block_indices = [
        index
        for index, block in enumerate(page.text_blocks)
        if index not in used_blocks and _block_inside_grid(block, row_edges, column_edges)
    ]
    detection = _build_table_from_grid(
        page,
        block_indices,
        row_edges,
        column_edges,
        strip_whitespace,
        borders={
            "top": "single",
            "bottom": "single",
            "left": "single",
            "right": "single",
            "insideH": "single",
            "insideV": "single",
        },
        border_color="000000",
        cell_padding=3.0,
    )
    if detection:
        detection.used_lines = {index for index, _ in horizontals + verticals}
        return [detection]
    return []


def _detect_tables_from_whitespace(
    page: Page,
    strip_whitespace: bool,
    used_blocks: set[int],
) -> Iterable[TableDetection]:
    candidates = [
        index
        for index, block in enumerate(page.text_blocks)
        if index not in used_blocks and block.text.strip()
    ]
    if len(candidates) < 4:
        return []

    detections: list[TableDetection] = []
    for cluster in _cluster_indices_by_bbox(candidates, page, tolerance=36.0):
        cluster = [index for index in cluster if index not in used_blocks]
        if len(cluster) < 4:
            continue
        row_edges = _grid_edges_from_centers(page, cluster, vertical=True)
        column_edges = _grid_edges_from_centers(page, cluster, vertical=False)
        row_count = len(row_edges) - 1
        column_count = len(column_edges) - 1
        if row_count < 2 or column_count < 2:
            continue
        detection = _build_table_from_grid(
            page,
            cluster,
            row_edges,
            column_edges,
            strip_whitespace,
            borders={
                "top": "single",
                "bottom": "single",
                "left": "single",
                "right": "single",
                "insideH": "single",
                "insideV": "single",
            },
            border_color="808080",
            cell_padding=2.5,
        )
        if detection and _table_has_tabular_density(detection.table):
            detections.append(detection)
    return detections


def _build_table_from_grid(
    page: Page,
    block_indices: Sequence[int],
    row_edges: Sequence[float],
    column_edges: Sequence[float],
    strip_whitespace: bool,
    *,
    borders: dict[str, str] | None,
    border_color: str | None,
    cell_padding: float | None,
) -> TableDetection | None:
    row_count = len(row_edges) - 1
    column_count = len(column_edges) - 1
    if row_count <= 0 or column_count <= 0:
        return None

    assignments: dict[tuple[int, int], CellData] = {}
    coverage: dict[tuple[int, int], tuple[int, int]] = {}
    skip_positions: set[tuple[int, int]] = set()
    vertical_positions: set[tuple[int, int]] = set()
    row_header_votes: defaultdict[int, int] = defaultdict(int)
    row_cell_counts: defaultdict[int, int] = defaultdict(int)
    used_block_indices: set[int] = set()

    for index in block_indices:
        block = page.text_blocks[index]
        row_start, row_end = _span_for_block(block, row_edges, vertical=True)
        col_start, col_end = _span_for_block(block, column_edges, vertical=False)
        key = (row_start, col_start)
        data = assignments.setdefault(key, CellData())
        data.blocks.append(index)
        data.row_span = max(data.row_span, row_end - row_start + 1)
        data.col_span = max(data.col_span, col_end - col_start + 1)
        role = (block.role or "").upper()
        if role in _HEADER_ROLES or block.bold:
            data.header = True
            data.background = data.background or _DEFAULT_HEADER_FILL
            data.vertical_alignment = data.vertical_alignment or "center"
            data.alignment = data.alignment or "center"
        elif role:
            alignment = _alignment_from_role(role)
            if alignment:
                data.alignment = data.alignment or alignment
        if data.alignment is None:
            data.alignment = _infer_cell_alignment(block)
        used_block_indices.add(index)
        row_cell_counts[row_start] += 1
        if data.header:
            row_header_votes[row_start] += 1
        for row in range(row_start, row_end + 1):
            for column in range(col_start, col_end + 1):
                coverage[(row, column)] = key
                if row == row_start and column > col_start:
                    skip_positions.add((row, column))
                if row > row_start and column == col_start:
                    vertical_positions.add((row, column))
                if row > row_start and column > col_start:
                    skip_positions.add((row, column))

    rows: list[TableRow] = []
    for row_index in range(row_count):
        row_cells: list[TableCell] = []
        start_keys: list[tuple[int, int]] = []
        column_index = 0
        while column_index < column_count:
            if (row_index, column_index) in skip_positions and (row_index, column_index) not in vertical_positions:
                column_index += 1
                continue
            key = coverage.get((row_index, column_index))
            if key is None:
                row_cells.append(TableCell())
                column_index += 1
                continue
            data = assignments[key]
            if key == (row_index, column_index):
                row_cells.append(_make_table_cell(page, data, strip_whitespace))
                start_keys.append(key)
                column_index += data.col_span
            elif (row_index, column_index) in vertical_positions:
                row_cells.append(
                    TableCell(
                        content=[],
                        row_span=1,
                        col_span=data.col_span,
                        row_span_continue=True,
                        alignment=data.alignment,
                        vertical_alignment=data.vertical_alignment,
                        background_color=data.background,
                    )
                )
                column_index += data.col_span
            else:
                column_index += 1
        is_header = False
        if row_cell_counts[row_index]:
            if row_header_votes[row_index] and row_header_votes[row_index] >= row_cell_counts[row_index]:
                is_header = True
        rows.append(TableRow(cells=row_cells, is_header=is_header))

    bbox = BoundingBox(
        left=column_edges[0],
        bottom=row_edges[-1],
        right=column_edges[-1],
        top=row_edges[0],
    )
    table_width = max(0.0, bbox.right - bbox.left)
    column_widths = [max(0.0, column_edges[index + 1] - column_edges[index]) for index in range(column_count)]
    table_alignment = _table_alignment(page.width, bbox.left, bbox.right)

    table = Table(
        rows=rows,
        width=table_width,
        column_widths=column_widths,
        borders=borders,
        border_color=border_color,
        alignment=table_alignment,
        cell_padding=cell_padding,
    )
    header_rows = 0
    for row in table.rows:
        if row.is_header:
            header_rows += 1
        else:
            break
    table.header_rows = header_rows
    return TableDetection(bbox=bbox, table=table, used_blocks=used_block_indices)


def _cluster_indices_by_bbox(
    indices: Sequence[int], page: Page, *, tolerance: float
) -> list[list[int]]:
    clusters: list[list[int]] = []
    for index in indices:
        block = page.text_blocks[index]
        assigned = False
        for cluster in clusters:
            if any(_boxes_close(block.bbox, page.text_blocks[other].bbox, tolerance) for other in cluster):
                cluster.append(index)
                assigned = True
                break
        if not assigned:
            clusters.append([index])
    return clusters


def _boxes_close(first: BoundingBox, second: BoundingBox, tolerance: float) -> bool:
    horizontal_gap = max(0.0, max(first.left, second.left) - min(first.right, second.right))
    vertical_gap = max(0.0, max(first.bottom, second.bottom) - min(first.top, second.top))
    return horizontal_gap <= tolerance and vertical_gap <= tolerance


def _cluster_positions(values: Sequence[float], *, tolerance: float, reverse: bool) -> list[float]:
    if not values:
        return []
    sorted_values = sorted(values, reverse=reverse)
    clusters: list[list[float]] = [[sorted_values[0]]]
    for value in sorted_values[1:]:
        if abs(clusters[-1][-1] - value) <= tolerance:
            clusters[-1].append(value)
        else:
            clusters.append([value])
    return [sum(cluster) / len(cluster) for cluster in clusters]


def _grid_edges_from_centers(page: Page, indices: Sequence[int], *, vertical: bool) -> list[float]:
    if not indices:
        return []
    if vertical:
        sizes = [page.text_blocks[index].bbox.top - page.text_blocks[index].bbox.bottom for index in indices]
        avg_size = sum(sizes) / len(sizes)
        tolerance = max(6.0, avg_size * 0.6)
        centers = [
            ((page.text_blocks[index].bbox.top + page.text_blocks[index].bbox.bottom) / 2, index)
            for index in indices
        ]
        centers.sort(reverse=True)
        boundary_start = max(page.text_blocks[index].bbox.top for index in indices)
        boundary_end = min(page.text_blocks[index].bbox.bottom for index in indices)
    else:
        sizes = [page.text_blocks[index].bbox.right - page.text_blocks[index].bbox.left for index in indices]
        avg_size = sum(sizes) / len(sizes)
        tolerance = max(6.0, avg_size * 0.6)
        table_left = min(page.text_blocks[index].bbox.left for index in indices)
        table_right = max(page.text_blocks[index].bbox.right for index in indices)
        table_width = max(1.0, table_right - table_left)
        narrow_indices = [
            index
            for index in indices
            if (page.text_blocks[index].bbox.right - page.text_blocks[index].bbox.left) <= table_width * 0.8
        ]
        indices_for_centers = narrow_indices if narrow_indices else list(indices)
        centers = [
            ((page.text_blocks[index].bbox.left + page.text_blocks[index].bbox.right) / 2, index)
            for index in indices_for_centers
        ]
        centers.sort()
        boundary_start = table_left
        boundary_end = table_right

    groups: list[tuple[float, list[int]]] = []
    for center, index in centers:
        if not groups:
            groups.append((center, [index]))
            continue
        current_center, items = groups[-1]
        if abs(current_center - center) <= tolerance:
            items.append(index)
            new_center = (current_center * (len(items) - 1) + center) / len(items)
            groups[-1] = (new_center, items)
        else:
            groups.append((center, [index]))

    if not groups:
        return [boundary_start, boundary_end]

    edges: list[float] = []
    if vertical:
        edges.append(boundary_start)
        for idx in range(len(groups) - 1):
            edges.append((groups[idx][0] + groups[idx + 1][0]) / 2)
        edges.append(boundary_end)
        return sorted(edges, reverse=True)

    edges.append(boundary_start)
    for idx in range(len(groups) - 1):
        edges.append((groups[idx][0] + groups[idx + 1][0]) / 2)
    edges.append(boundary_end)
    return sorted(edges)


def _span_for_block(block: TextBlock, edges: Sequence[float], *, vertical: bool) -> tuple[int, int]:
    if len(edges) < 2:
        return 0, 0
    top_value = block.bbox.top if vertical else block.bbox.left
    bottom_value = block.bbox.bottom if vertical else block.bbox.right
    start = _index_for_coordinate(top_value, edges, vertical=vertical, prefer_lower=False)
    end = _index_for_coordinate(bottom_value, edges, vertical=vertical, prefer_lower=True)
    if end < start:
        end = start
    max_index = len(edges) - 2
    return max(0, min(start, max_index)), max(0, min(end, max_index))


def _index_for_coordinate(
    value: float,
    edges: Sequence[float],
    *,
    vertical: bool,
    prefer_lower: bool,
) -> int:
    tolerance = 2.0
    if vertical:
        for index in range(len(edges) - 1):
            upper = edges[index]
            lower = edges[index + 1]
            if value <= upper + tolerance and value >= lower - tolerance:
                return index
        return len(edges) - 2 if prefer_lower else 0
    for index in range(len(edges) - 1):
        left = edges[index]
        right = edges[index + 1]
        if value >= left - tolerance and value <= right + tolerance:
            return index
    return len(edges) - 2 if prefer_lower else 0


def _block_inside_grid(block: TextBlock, row_edges: Sequence[float], column_edges: Sequence[float]) -> bool:
    if len(row_edges) < 2 or len(column_edges) < 2:
        return False
    center_x = (block.bbox.left + block.bbox.right) / 2
    center_y = (block.bbox.top + block.bbox.bottom) / 2
    within_rows = row_edges[-1] <= center_y <= row_edges[0]
    within_columns = column_edges[0] <= center_x <= column_edges[-1]
    return within_rows and within_columns


def _make_table_cell(page: Page, data: CellData, strip_whitespace: bool) -> TableCell:
    blocks = [page.text_blocks[index] for index in data.blocks]
    paragraphs = blocks_to_paragraphs_static(blocks, strip_whitespace, alignment=data.alignment)
    cell = TableCell(
        content=paragraphs,
        row_span=data.row_span,
        col_span=data.col_span,
        alignment=data.alignment,
        vertical_alignment=data.vertical_alignment,
        background_color=data.background,
    )
    return cell


def _alignment_from_role(role: str) -> str | None:
    if role in {"CENTER", "TABLEHEADER"}:
        return "center"
    if role in {"RIGHT", "TABLERIGHT"}:
        return "right"
    if role in {"LEFT", "TABLELEFT"}:
        return "left"
    return None


def _infer_cell_alignment(block: TextBlock) -> str | None:
    text = (block.text or "").strip()
    if not text:
        return None
    if _looks_numeric(text):
        return "right"
    if len(text) <= 3 and text.isalpha():
        return "center"
    return None


def _looks_numeric(text: str) -> bool:
    cleaned = text.replace(",", "").replace("\u2212", "-").replace("·", "").strip()
    if not cleaned:
        return False
    try:
        float(cleaned)
        return True
    except ValueError:
        return False


def _table_has_tabular_density(table: Table) -> bool:
    if not table.rows:
        return False
    populated_rows = sum(1 for row in table.rows if any(cell.content for cell in row.cells))
    max_columns = max(len(row.cells) for row in table.rows)
    return populated_rows >= 2 and max_columns >= 2


def _table_alignment(page_width: float, left: float, right: float) -> str | None:
    width = max(1.0, right - left)
    center = (left + right) / 2
    page_center = page_width / 2
    if abs(center - page_center) <= max(12.0, width * 0.15):
        return "center"
    if center < page_center:
        return "left"
    return "right"


def infer_columns(page: Page) -> tuple[int, float | None]:
    if not page.text_blocks:
        return 1, None
    positions = sorted(block.bbox.left for block in page.text_blocks)
    if len(positions) < 4:
        return 1, None
    gaps = [positions[index + 1] - positions[index] for index in range(len(positions) - 1)]
    if not gaps:
        return 1, None
    average_gap = sum(gaps) / len(gaps)
    large_gaps = [gap for gap in gaps if gap > average_gap * 2]
    if len(large_gaps) >= 1:
        columns = min(len(large_gaps) + 1, 3)
        spacing = min(large_gaps)
        return columns, spacing
    return 1, None


def assign_headers_footers(
    document,
    page_elements: Mapping[int, list[BlockElement]],
    page_section_map: Mapping[int, Section],
) -> None:
    for section in document.iter_sections():
        pages = sorted(page for page, sec in page_section_map.items() if sec is section)
        if not pages:
            continue
        section.header = None
        section.footer = None
        section.first_page_header = None
        section.first_page_footer = None

        header_candidates = _collect_region_candidates(pages, section, page_elements, kind="header")
        footer_candidates = _collect_region_candidates(pages, section, page_elements, kind="footer")

        removal_ids: set[int] = set()

        header_signature, header_pages = _select_repeating_signature(header_candidates, pages)
        if header_signature and header_pages:
            default_candidate = header_candidates[header_pages[0]]
            section.header = _build_header_footer_container(default_candidate)
            for page in header_pages:
                removal_ids.update(id(paragraph) for paragraph in header_candidates[page].paragraphs)
            first_header = _first_page_candidate(header_candidates, header_pages, pages)
            if first_header is not None:
                section.first_page_header = _build_header_footer_container(first_header)
                removal_ids.update(id(paragraph) for paragraph in first_header.paragraphs)

        footer_signature, footer_pages = _select_repeating_signature(footer_candidates, pages)
        if footer_signature and footer_pages:
            default_footer = footer_candidates[footer_pages[0]]
            section.footer = _build_header_footer_container(default_footer, include_page_numbers=True)
            for page in footer_pages:
                removal_ids.update(id(paragraph) for paragraph in footer_candidates[page].paragraphs)
            first_footer = _first_page_candidate(footer_candidates, footer_pages, pages)
            if first_footer is not None:
                section.first_page_footer = _build_header_footer_container(first_footer, include_page_numbers=True)
                removal_ids.update(id(paragraph) for paragraph in first_footer.paragraphs)

        if removal_ids:
            _remove_elements_from_section(section, page_elements, removal_ids)


def _paragraph_is_page_local(paragraph: Paragraph, page: int) -> bool:
    metadata = paragraph.metadata or {}
    start = int(metadata.get("start_page", page))
    end = int(metadata.get("end_page", start))
    return start == end == page


def _metadata_float(paragraph: Paragraph, key: str) -> float | None:
    metadata = paragraph.metadata or {}
    value = metadata.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _collect_region_candidates(
    pages: Sequence[int],
    section: Section,
    page_elements: Mapping[int, list[BlockElement]],
    *,
    kind: str,
) -> dict[int, _RegionCandidate]:
    candidates: dict[int, _RegionCandidate] = {}
    for page in pages:
        elements = page_elements.get(page, [])
        region: list[tuple[float, Paragraph]] = []
        for element in elements:
            if not isinstance(element, Paragraph) or not _paragraph_is_page_local(element, page):
                continue
            top = _metadata_float(element, "bbox_top")
            bottom = _metadata_float(element, "bbox_bottom")
            if top is None or bottom is None:
                continue
            if kind == "header":
                distance = section.page_height - top
                limit = section.margin_top + _REGION_TOLERANCE
                if distance <= limit:
                    region.append((top, element))
            else:
                distance = bottom
                limit = section.margin_bottom + _REGION_TOLERANCE
                if distance <= limit:
                    region.append((bottom, element))
        if not region:
            continue
        if kind == "header":
            region.sort(key=lambda item: item[0], reverse=True)
        else:
            region.sort(key=lambda item: item[0])
        paragraphs = [item[1] for item in region[:_MAX_REGION_PARAGRAPHS]]
        signature = tuple(
            _normalise_signature_text(paragraph, strip_digits=(kind == "footer"))
            for paragraph in paragraphs
            if paragraph.text().strip()
        )
        candidates[page] = _RegionCandidate(page=page, paragraphs=paragraphs, signature=signature)
    return candidates


def _select_repeating_signature(
    candidates: Mapping[int, _RegionCandidate],
    pages: Sequence[int],
) -> tuple[tuple[str, ...] | None, list[int]]:
    signatures = Counter(
        candidate.signature for candidate in candidates.values() if candidate.signature
    )
    if not signatures:
        return None, []
    signature, count = signatures.most_common(1)[0]
    if count < 2:
        return None, []
    matched_pages = [
        page
        for page in pages
        if page in candidates and candidates[page].signature == signature
    ]
    return signature, matched_pages


def _first_page_candidate(
    candidates: Mapping[int, _RegionCandidate],
    matched_pages: Sequence[int],
    pages: Sequence[int],
) -> _RegionCandidate | None:
    if not matched_pages or not pages:
        return None
    first_page = pages[0]
    if first_page in matched_pages:
        return None
    candidate = candidates.get(first_page)
    if candidate is None or not candidate.paragraphs:
        return None
    return candidate


def _normalise_signature_text(paragraph: Paragraph, *, strip_digits: bool) -> str:
    text = paragraph.text().strip()
    if not text:
        return ""
    working = text
    if strip_digits:
        working = _DIGIT_RE.sub("", working)
    cleaned = _SPACE_RE.sub(" ", working).strip().lower()
    if cleaned:
        return cleaned
    return _SPACE_RE.sub(" ", text).strip().lower()


def _build_header_footer_container(
    candidate: _RegionCandidate,
    *,
    include_page_numbers: bool = False,
) -> HeaderFooter:
    content = [deepcopy(paragraph) for paragraph in candidate.paragraphs]
    for paragraph in content:
        if isinstance(paragraph, Paragraph):
            paragraph.metadata = None
    metadata = {"page_numbers": "true"} if include_page_numbers else None
    return HeaderFooter(content=content, metadata=metadata)


def _remove_elements_from_section(
    section: Section,
    page_elements: Mapping[int, list[BlockElement]],
    removal_ids: set[int],
) -> None:
    section.elements = [element for element in section.elements if id(element) not in removal_ids]
    for elements in page_elements.values():
        elements[:] = [element for element in elements if id(element) not in removal_ids]
