"""PDF reader integration utilities."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import atan2, degrees
from typing import Any, ClassVar, Iterable, Mapping, Sequence

from pypdf import PdfReader
from pypdf._page import ContentStream
from pypdf.generic import (
    ArrayObject,
    Destination,
    DictionaryObject,
    IndirectObject,
    NameObject,
    TextStringObject,
)

from ..primitives import (
    BoundingBox,
    FormField,
    Line,
    Link,
    OutlineNode,
    Page,
    Path,
    PdfAnnotation,
)
from .fonts import apply_translation_map, font_translation_maps
from .images import extract_page_images
from .text import CapturedText, is_east_asian_text, text_fragments_to_blocks

__all__ = [
    "ContentStreamState",
    "capture_text_fragments",
    "extract_outline",
    "extract_vector_graphics",
    "extract_struct_roles",
    "page_from_reader",
    "summarise_content_stream_commands",
    "_is_vertical_matrix",
]


def _is_vertical_matrix(matrix: list[float] | None) -> bool:
    if not matrix or len(matrix) < 4:
        return False
    a, b, c, d = matrix[0], matrix[1], matrix[2], matrix[3]

    def _is_ninety(angle: float) -> bool:
        angle = (angle + 360.0) % 360.0
        return min(abs(angle - 90.0), abs(angle - 270.0)) <= 15.0

    try:
        primary = degrees(atan2(b, a))
        secondary = degrees(atan2(-c, d))
    except Exception:
        return False
    if _is_ninety(primary) or _is_ninety(secondary):
        return True
    if abs(a) < 1e-3 and abs(d) < 1e-3 and (abs(b) > 0 or abs(c) > 0):
        return True
    return False


def _normalise_anchor_name(base: str, *, page_index: int | None, top: float | None) -> str:
    cleaned = [ch for ch in base if ch.isalnum() or ch in {"_", "-"}]
    if not cleaned:
        cleaned = ["dest"]
    anchor = "".join(cleaned)
    if anchor[0].isdigit():
        anchor = f"dest_{anchor}"
    if page_index is not None:
        anchor = f"{anchor}_p{page_index}"
    if top is not None:
        anchor = f"{anchor}_y{int(top)}"
    return anchor[:40]


def _resolve_indirect(obj: object | None) -> object | None:
    if isinstance(obj, IndirectObject):
        try:
            return obj.get_object()
        except Exception:
            return None
    return obj


@dataclass(slots=True)
class ContentStreamState:
    """Graphics state snapshot for a page content stream."""

    IDENTITY_MATRIX: ClassVar[tuple[float, float, float, float, float, float]] = (
        1.0,
        0.0,
        0.0,
        1.0,
        0.0,
        0.0,
    )

    ctm: tuple[float, float, float, float, float, float] = IDENTITY_MATRIX
    text_matrix: tuple[float, float, float, float, float, float] = IDENTITY_MATRIX
    line_matrix: tuple[float, float, float, float, float, float] = IDENTITY_MATRIX
    font_ref: NameObject | None = None
    font_name: str | None = None
    font_size: float | None = None
    fill_color: tuple[float, float, float] = (0.0, 0.0, 0.0)
    stroke_color: tuple[float, float, float] = (0.0, 0.0, 0.0)
    character_spacing: float = 0.0
    word_spacing: float = 0.0
    horizontal_scaling: float = 100.0
    leading: float = 0.0
    text_objects: int = 0
    graphics_stack_depth: int = 1
    max_graphics_stack_depth: int = 1
    last_text_position: tuple[float, float] = (0.0, 0.0)

    def reset(self) -> None:
        """Reset the graphics state to PDF specification defaults."""

        self.ctm = self.IDENTITY_MATRIX
        self.text_matrix = self.IDENTITY_MATRIX
        self.line_matrix = self.IDENTITY_MATRIX
        self.font_ref = None
        self.font_name = None
        self.font_size = None
        self.fill_color = (0.0, 0.0, 0.0)
        self.stroke_color = (0.0, 0.0, 0.0)
        self.character_spacing = 0.0
        self.word_spacing = 0.0
        self.horizontal_scaling = 100.0
        self.leading = 0.0
        self.text_objects = 0
        self.graphics_stack_depth = 1
        self.max_graphics_stack_depth = 1
        self.last_text_position = (0.0, 0.0)

    def snapshot(self, *, page_number: int | None = None) -> dict[str, Any]:
        """Return a serialisable view of the current graphics state."""

        data: dict[str, Any] = {
            "ctm": tuple(self.ctm),
            "text_matrix": tuple(self.text_matrix),
            "line_matrix": tuple(self.line_matrix),
            "font_ref": str(self.font_ref) if self.font_ref is not None else None,
            "font_name": self.font_name,
            "font_size": float(self.font_size) if self.font_size is not None else None,
            "fill_color": tuple(self.fill_color),
            "stroke_color": tuple(self.stroke_color),
            "character_spacing": float(self.character_spacing),
            "word_spacing": float(self.word_spacing),
            "horizontal_scaling": float(self.horizontal_scaling),
            "leading": float(self.leading),
            "text_objects": int(self.text_objects),
            "graphics_stack_depth": int(self.graphics_stack_depth),
            "max_graphics_stack_depth": int(self.max_graphics_stack_depth),
            "last_text_position": (
                float(self.last_text_position[0]),
                float(self.last_text_position[1]),
            ),
        }
        if page_number is not None:
            data["page_number"] = page_number
        return data


_TEXT_CONTROL_OPS = {b"BT", b"ET"}
_TEXT_STATE_OPS = {b"Tc", b"Tw", b"TL", b"Tz", b"Tr", b"Ts", b"d0", b"d1"}
_TEXT_POSITION_OPS = {b"Td", b"TD", b"Tm", b"T*"}
_TEXT_SHOW_OPS = {b"Tj", b"TJ", b"'", b'"'}
_GRAPHICS_STATE_OPS = {b"q", b"Q", b"cm", b"gs", b"w", b"J", b"j", b"M", b"d", b"ri", b"i"}
_COLOR_OPS = {
    b"RG",
    b"rg",
    b"G",
    b"g",
    b"K",
    b"k",
    b"CS",
    b"cs",
    b"SC",
    b"sc",
    b"SCN",
    b"scn",
}
_PATH_CONSTRUCTION_OPS = {b"m", b"l", b"c", b"v", b"y", b"h", b"re"}
_PATH_PAINTING_OPS = {b"S", b"s", b"f", b"F", b"f*", b"B", b"B*", b"b", b"b*", b"n"}
_CLIPPING_OPS = {b"W", b"W*"}
_XOBJECT_OPS = {b"Do"}
_INLINE_IMAGE_OPS = {b"BI", b"ID", b"EI"}
_MARKED_CONTENT_OPS = {b"BMC", b"BDC", b"EMC", b"MP", b"DP", b"BX", b"EX"}
_SHADING_OPS = {b"sh"}


def _decode_operator(operator: object) -> bytes:
    if isinstance(operator, bytes):
        return operator
    if isinstance(operator, str):
        return operator.encode("latin-1", "ignore")
    return str(operator).encode("latin-1", "ignore")


def _classify_operator(operator: bytes) -> str:
    if operator in _TEXT_CONTROL_OPS:
        return "text_control"
    if operator in _TEXT_STATE_OPS:
        return "text_state"
    if operator in _TEXT_POSITION_OPS:
        return "text_position"
    if operator in _TEXT_SHOW_OPS:
        return "text_show"
    if operator in _GRAPHICS_STATE_OPS:
        return "graphics_state"
    if operator in _COLOR_OPS:
        return "color"
    if operator in _PATH_CONSTRUCTION_OPS:
        return "path_construction"
    if operator in _PATH_PAINTING_OPS:
        return "path_painting"
    if operator in _CLIPPING_OPS:
        return "clipping"
    if operator in _XOBJECT_OPS:
        return "xobject"
    if operator in _INLINE_IMAGE_OPS:
        return "inline_image"
    if operator in _MARKED_CONTENT_OPS:
        return "marked_content"
    if operator in _SHADING_OPS:
        return "shading"
    return "unknown"


def summarise_content_stream_commands(
    page: DictionaryObject,
    reader: PdfReader,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    """Parse a content stream and classify each operator encountered."""

    try:
        content = ContentStream(page.get_contents(), reader)
    except Exception:
        return (
            [],
            {
                "command_count": 0,
                "recognised": 0,
                "unknown_commands": 0,
                "text_control_commands": 0,
                "text_state_commands": 0,
                "text_position_commands": 0,
                "text_show_commands": 0,
                "graphics_state_commands": 0,
                "color_commands": 0,
                "path_construction_commands": 0,
                "path_painting_commands": 0,
                "clipping_commands": 0,
                "inline_image_commands": 0,
                "xobject_commands": 0,
                "marked_content_commands": 0,
                "shading_commands": 0,
                "operators": [],
            },
            [],
        )

    resources = page.get(NameObject("/Resources"))
    fonts_dict = None
    if isinstance(resources, DictionaryObject):
        fonts_dict = resources.get(NameObject("/Font"))

    operations = getattr(content, "operations", [])
    commands: list[dict[str, Any]] = []
    counts = {
        "text_control": 0,
        "text_state": 0,
        "text_position": 0,
        "text_show": 0,
        "graphics_state": 0,
        "color": 0,
        "path_construction": 0,
        "path_painting": 0,
        "clipping": 0,
        "inline_image": 0,
        "xobject": 0,
        "marked_content": 0,
        "shading": 0,
        "unknown": 0,
    }
    operators_seen: set[str] = set()

    matrix_stack: list[tuple[float, float, float, float, float, float]] = [
        ContentStreamState.IDENTITY_MATRIX
    ]
    text_matrix: tuple[float, float, float, float, float, float] | None = None
    line_matrix: tuple[float, float, float, float, float, float] | None = None
    current_font_ref: NameObject | None = None
    current_font_name: str | None = None
    current_font_size: float | None = None
    leading: float = 0.0
    text_state_changes: list[dict[str, Any]] = []
    last_position: tuple[float, float] = (0.0, 0.0)

    def _resolve_font(ref: object | None) -> tuple[str | None, NameObject | None]:
        if ref is None or not isinstance(fonts_dict, DictionaryObject):
            return None, None
        raw_name = str(ref)
        candidate_names = {raw_name}
        if raw_name.startswith("/"):
            candidate_names.add(raw_name[1:])
        else:
            candidate_names.add("/" + raw_name)
        for key, value in fonts_dict.items():
            key_name = str(key)
            if key_name not in candidate_names and key_name.lstrip("/") not in candidate_names:
                continue
            resolved = value
            if isinstance(resolved, IndirectObject):
                try:
                    resolved = resolved.get_object()
                except Exception:
                    resolved = None
            base_font = None
            if isinstance(resolved, DictionaryObject):
                base_font_obj = (
                    resolved.get(NameObject("/BaseFont"))
                    or resolved.get("/BaseFont")
                )
                if base_font_obj is not None:
                    base_font = str(base_font_obj)
                    if base_font.startswith("/"):
                        base_font = base_font[1:]
            normalised_key = key if isinstance(key, NameObject) else NameObject(str(key))
            return base_font, normalised_key
        return None, None

    def _record_position_change(
        operator_name: str,
        matrix: tuple[float, float, float, float, float, float],
    ) -> None:
        nonlocal last_position
        try:
            combined = _matrix_multiply(matrix_stack[-1], matrix)
            x, y = _matrix_apply(combined, 0.0, 0.0)
            last_position = (float(x), float(y))
        except Exception:
            last_position = (0.0, 0.0)
        entry: dict[str, Any] = {
            "operator": operator_name,
            "position": last_position,
            "text_matrix": tuple(matrix),
            "ctm": tuple(matrix_stack[-1]),
        }
        if current_font_name is not None:
            entry["font_name"] = current_font_name
        if current_font_size is not None:
            entry["font_size"] = float(current_font_size)
        if operator_name == "TD":
            entry["leading"] = float(leading)
        text_state_changes.append(entry)

    def _record_font_change(
        operator_name: str,
        font_name: str | None,
        font_ref: NameObject | None,
        font_size: float | None,
        font_resource: object | None,
    ) -> None:
        entry: dict[str, Any] = {
            "operator": operator_name,
        }
        if font_resource is not None:
            entry["font_resource"] = str(font_resource)
        elif font_ref is not None:
            entry["font_resource"] = str(font_ref)
        if font_name is not None:
            entry["font_name"] = font_name
        if font_size is not None:
            entry["font_size"] = float(font_size)
        if text_matrix is not None:
            try:
                combined = _matrix_multiply(matrix_stack[-1], text_matrix)
                x, y = _matrix_apply(combined, 0.0, 0.0)
                entry["position"] = (float(x), float(y))
            except Exception:
                entry["position"] = last_position
        text_state_changes.append(entry)

    for operands, operator in operations:
        op_bytes = _decode_operator(operator)
        category = _classify_operator(op_bytes)
        operand_count = len(operands) if isinstance(operands, (list, tuple)) else 0
        operator_name = op_bytes.decode("latin-1", "ignore")
        operators_seen.add(operator_name)
        counts[category] = counts.get(category, 0) + 1
        commands.append(
            {
                "operator": operator_name,
                "category": category,
                "operand_count": operand_count,
                "recognised": category != "unknown",
            }
        )

        if op_bytes == b"q":
            matrix_stack.append(matrix_stack[-1])
        elif op_bytes == b"Q":
            if len(matrix_stack) > 1:
                matrix_stack.pop()
        elif op_bytes == b"cm" and len(operands) == 6:
            try:
                matrix = tuple(float(value) for value in operands)
                matrix_stack[-1] = _matrix_multiply(matrix_stack[-1], matrix)
            except Exception:
                pass
        elif op_bytes == b"BT":
            text_matrix = ContentStreamState.IDENTITY_MATRIX
            line_matrix = text_matrix
        elif op_bytes == b"ET":
            text_matrix = None
            line_matrix = None
        elif op_bytes == b"Tf" and len(operands) >= 2:
            try:
                font_ref_operand = operands[0]
                font_size = float(operands[1])
            except Exception:
                font_ref_operand = None
                font_size = None
            font_name, resolved_ref = _resolve_font(font_ref_operand)
            normalised_ref: NameObject | None
            if resolved_ref is not None:
                normalised_ref = resolved_ref
            elif isinstance(font_ref_operand, NameObject):
                normalised_ref = font_ref_operand
            elif isinstance(font_ref_operand, str):
                candidate = font_ref_operand
                if not candidate.startswith("/"):
                    candidate = f"/{candidate}"
                try:
                    normalised_ref = NameObject(candidate)
                except Exception:
                    normalised_ref = None
            else:
                normalised_ref = None
            current_font_ref = normalised_ref
            current_font_name = font_name
            current_font_size = font_size
            _record_font_change(
                "Tf",
                current_font_name,
                current_font_ref,
                current_font_size,
                font_ref_operand,
            )
        elif op_bytes == b"Tm" and len(operands) >= 6:
            try:
                tm = tuple(float(operands[i]) for i in range(6))
                text_matrix = tm
                line_matrix = tm
                _record_position_change("Tm", tm)
            except Exception:
                pass
        elif op_bytes in {b"Td", b"TD"} and len(operands) >= 2:
            if line_matrix is None:
                continue
            try:
                tx = float(operands[0])
                ty = float(operands[1])
                translate = (1.0, 0.0, 0.0, 1.0, tx, ty)
                line_matrix = _matrix_multiply(line_matrix, translate)
                text_matrix = line_matrix
                if op_bytes == b"TD":
                    leading = -ty
                _record_position_change(operator_name, line_matrix)
            except Exception:
                pass
        elif op_bytes == b"T*" and line_matrix is not None:
            try:
                ty = -1.2 * (current_font_size or 12.0)
                translate = (1.0, 0.0, 0.0, 1.0, 0.0, ty)
                line_matrix = _matrix_multiply(line_matrix, translate)
                text_matrix = line_matrix
                _record_position_change("T*", line_matrix)
            except Exception:
                pass
        elif op_bytes == b"Tc" and operands:
            try:
                _ = float(operands[0])
            except Exception:
                pass
        elif op_bytes == b"Tw" and operands:
            try:
                _ = float(operands[0])
            except Exception:
                pass
        elif op_bytes == b"Tz" and operands:
            try:
                _ = float(operands[0])
            except Exception:
                pass
        elif op_bytes == b"TL" and operands:
            try:
                leading = float(operands[0])
            except Exception:
                pass

    summary = {
        "command_count": len(commands),
        "recognised": len(commands) - counts.get("unknown", 0),
        "unknown_commands": counts.get("unknown", 0),
        "text_control_commands": counts.get("text_control", 0),
        "text_state_commands": counts.get("text_state", 0),
        "text_position_commands": counts.get("text_position", 0),
        "text_show_commands": counts.get("text_show", 0),
        "graphics_state_commands": counts.get("graphics_state", 0),
        "color_commands": counts.get("color", 0),
        "path_construction_commands": counts.get("path_construction", 0),
        "path_painting_commands": counts.get("path_painting", 0),
        "clipping_commands": counts.get("clipping", 0),
        "inline_image_commands": counts.get("inline_image", 0),
        "xobject_commands": counts.get("xobject", 0),
        "marked_content_commands": counts.get("marked_content", 0),
        "shading_commands": counts.get("shading", 0),
        "operators": sorted(operators_seen),
        "text_state_change_count": len(text_state_changes),
        "font_state_changes": sum(1 for entry in text_state_changes if entry.get("operator") == "Tf"),
        "position_state_changes": sum(
            1
            for entry in text_state_changes
            if entry.get("operator") in {"Td", "TD", "Tm", "T*"}
        ),
    }

    return commands, summary, text_state_changes


@dataclass(slots=True)
class _GraphicsState:
    line_width: float = 1.0
    stroke_color: tuple[float, float, float] = (0.0, 0.0, 0.0)
    fill_color: tuple[float, float, float] = (0.0, 0.0, 0.0)
    stroke_alpha: float = 1.0
    fill_alpha: float = 1.0

    def clone(self) -> "_GraphicsState":
        return _GraphicsState(
            line_width=self.line_width,
            stroke_color=self.stroke_color,
            fill_color=self.fill_color,
            stroke_alpha=self.stroke_alpha,
            fill_alpha=self.fill_alpha,
        )


def _page_index_from_ref(reader: PdfReader, candidate: object | None) -> int | None:
    resolved = _resolve_indirect(candidate)
    if isinstance(resolved, IndirectObject):
        candidate = resolved
    if isinstance(candidate, IndirectObject):
        for index, page in enumerate(reader.pages):
            ref = getattr(page, "indirect_reference", None)
            if isinstance(ref, IndirectObject) and ref.idnum == candidate.idnum and ref.generation == candidate.generation:
                return index
    if isinstance(resolved, DictionaryObject):
        for index, page in enumerate(reader.pages):
            if page is resolved or page == resolved:
                return index
    return None


def _resolve_destination(
    reader: PdfReader,
    dest: object | None,
) -> tuple[str | None, int | None, float | None]:
    dest = _resolve_indirect(dest)
    anchor: str | None = None
    page_index: int | None = None
    top: float | None = None

    if isinstance(dest, Destination):
        page_index = _page_index_from_ref(reader, dest.page)
        top = getattr(dest, "top", None)
        anchor = _normalise_anchor_name(dest.title or "dest", page_index=page_index, top=top)
        return anchor, page_index, top

    if isinstance(dest, NameObject):
        name = str(dest)
        key = name[1:] if name.startswith("/") else name
        named = None
        try:
            named = reader.named_destinations.get(key)  # type: ignore[attr-defined]
        except Exception:
            named = None
        if named is not None:
            page_index = _page_index_from_ref(reader, getattr(named, "page", None))
            top = getattr(named, "top", None)
        anchor = _normalise_anchor_name(key or "dest", page_index=page_index, top=top)
        return anchor, page_index, top

    if isinstance(dest, ArrayObject) and dest:
        page_index = _page_index_from_ref(reader, dest[0])
        if len(dest) >= 4:
            try:
                top = float(dest[3])
            except Exception:
                top = None
        anchor = _normalise_anchor_name("dest", page_index=page_index, top=top)
        return anchor, page_index, top

    return None, None, None


def _extract_links(page: DictionaryObject, reader: PdfReader) -> list[Link]:
    annotations = _resolve_indirect(page.get(NameObject("/Annots")))
    if not isinstance(annotations, ArrayObject):
        return []
    links: list[Link] = []
    for entry in annotations:
        annot = _resolve_indirect(entry)
        if not isinstance(annot, DictionaryObject):
            continue
        subtype = annot.get(NameObject("/Subtype"))
        if str(subtype) not in {"/Link", "Link"}:
            continue
        rect = _resolve_indirect(annot.get(NameObject("/Rect")))
        if not isinstance(rect, ArrayObject) or len(rect) < 4:
            continue
        try:
            left, bottom, right, top = [float(rect[i]) for i in range(4)]
        except Exception:
            continue
        bbox = BoundingBox(
            left=min(left, right),
            bottom=min(bottom, top),
            right=max(left, right),
            top=max(bottom, top),
        )
        tooltip_obj = annot.get(NameObject("/Contents"))
        tooltip = str(tooltip_obj) if isinstance(tooltip_obj, TextStringObject) else None
        link = Link(bbox=bbox, tooltip=tooltip)

        action = _resolve_indirect(annot.get(NameObject("/A")))
        if isinstance(action, DictionaryObject):
            kind = action.get(NameObject("/S"))
            if str(kind) == "/URI":
                uri_obj = _resolve_indirect(action.get(NameObject("/URI")))
                if uri_obj is not None:
                    link.uri = str(uri_obj)
                    link.kind = "external"
            elif str(kind) == "/GoTo":
                dest = action.get(NameObject("/D"))
                anchor, page_index, top = _resolve_destination(reader, dest)
                link.anchor = anchor
                link.destination_page = page_index
                link.destination_top = top
                link.kind = "internal"
            elif str(kind) == "/GoToR":
                file_spec = _resolve_indirect(action.get(NameObject("/F")))
                if file_spec is not None:
                    link.uri = f"file:{file_spec}"
                    link.kind = "file"
            elif str(kind) == "/Launch":
                target = action.get(NameObject("/F"))
                if target is not None:
                    link.uri = f"file:{target}"
                    link.kind = "file"

        if link.uri is None:
            uri_obj = _resolve_indirect(annot.get(NameObject("/URI")))
            if uri_obj is not None:
                link.uri = str(uri_obj)
                link.kind = "external"
        if link.anchor is None:
            dest = annot.get(NameObject("/Dest"))
            if dest is not None:
                anchor, page_index, top = _resolve_destination(reader, dest)
                link.anchor = anchor
                link.destination_page = page_index
                link.destination_top = top
                link.kind = "internal"
        if link.uri is None and link.anchor is None:
            continue
        links.append(link)
    return links


def _int_value(value: object | None) -> int:
    value = _resolve_indirect(value)
    if value is None:
        return 0
    try:
        return int(value)  # type: ignore[arg-type]
    except Exception:
        try:
            if isinstance(value, str) and value.strip():
                return int(float(value))
        except Exception:
            return 0
    return 0


def _stringify_pdf_object(value: object | None) -> str | None:
    value = _resolve_indirect(value)
    if value is None:
        return None
    if isinstance(value, TextStringObject):
        return str(value)
    if isinstance(value, NameObject):
        raw = str(value)
        return raw[1:] if raw.startswith("/") else raw
    if isinstance(value, ArrayObject):
        parts = [part for part in (_stringify_pdf_object(item) for item in value) if part]
        if parts:
            return ", ".join(parts)
        return None
    try:
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, bytes):
            return value.decode("utf-8", "ignore")
    except Exception:
        return None
    try:
        return str(value)
    except Exception:
        return None


def _checkbox_checked(state: str | None) -> bool:
    if not state:
        return False
    cleaned = state.strip().lower()
    return cleaned not in {"off", "no", "0"}


def _choice_options(field: DictionaryObject) -> list[str]:
    raw = _resolve_indirect(field.get(NameObject("/Opt")))
    if not isinstance(raw, ArrayObject):
        return []
    options: list[str] = []
    for entry in raw:
        resolved = _resolve_indirect(entry)
        if isinstance(resolved, ArrayObject) and resolved:
            display = _stringify_pdf_object(resolved[-1])
        else:
            display = _stringify_pdf_object(resolved)
        if display:
            options.append(display)
    return options


def _extract_form_fields(page: DictionaryObject) -> list[FormField]:
    annotations = _resolve_indirect(page.get(NameObject("/Annots")))
    if not isinstance(annotations, ArrayObject):
        return []
    fields: list[FormField] = []
    for entry in annotations:
        widget = _resolve_indirect(entry)
        if not isinstance(widget, DictionaryObject):
            continue
        subtype = widget.get(NameObject("/Subtype"))
        if str(subtype) not in {"/Widget", "Widget"}:
            continue
        parent = _resolve_indirect(widget.get(NameObject("/Parent")))
        if isinstance(parent, DictionaryObject):
            field_dict = parent
        else:
            field_dict = widget
        ft_obj = field_dict.get(NameObject("/FT"))
        if ft_obj is None:
            continue
        field_type_name = _clean_name(ft_obj)
        field_type_lower = field_type_name.lower()
        if not field_type_lower:
            continue
        flags = _int_value(field_dict.get(NameObject("/Ff")))
        if field_type_lower == "btn" and flags & 0x10000:
            # Push buttons do not carry user-visible values
            continue
        rect_obj = _resolve_indirect(widget.get(NameObject("/Rect"))) or _resolve_indirect(
            field_dict.get(NameObject("/Rect"))
        )
        if not isinstance(rect_obj, ArrayObject) or len(rect_obj) < 4:
            continue
        try:
            left, bottom, right, top = [float(rect_obj[i]) for i in range(4)]
        except Exception:
            continue
        bbox = BoundingBox(
            left=min(left, right),
            bottom=min(bottom, top),
            right=max(left, right),
            top=max(bottom, top),
        )
        field_name = _stringify_pdf_object(field_dict.get(NameObject("/T")))
        alt_label = _stringify_pdf_object(widget.get(NameObject("/TU"))) or _stringify_pdf_object(
            field_dict.get(NameObject("/TU"))
        )
        label = alt_label or field_name or field_type_name.title()
        tooltip: str | None = None
        for candidate in (field_name, alt_label):
            if candidate and candidate != label:
                tooltip = candidate
                break
        value_obj = field_dict.get(NameObject("/V")) or widget.get(NameObject("/V"))
        if value_obj is None:
            value_obj = field_dict.get(NameObject("/DV"))
        resolved_value = _resolve_indirect(value_obj)
        read_only = bool(flags & 0x1)
        multiline = bool(flags & 0x1000)

        kind = field_type_lower
        value_text: str | None = None
        checked: bool | None = None
        options: list[str] = []

        if field_type_lower == "tx":
            kind = "text"
            value_text = _stringify_pdf_object(resolved_value)
        elif field_type_lower == "btn":
            kind = "checkbox"
            state = _stringify_pdf_object(resolved_value) or _stringify_pdf_object(
                widget.get(NameObject("/AS"))
            )
            checked = _checkbox_checked(state)
            value_text = state if state and state.lower() not in {"off", "0"} else None
        elif field_type_lower == "ch":
            kind = "dropdown"
            options = _choice_options(field_dict)
            if isinstance(resolved_value, ArrayObject):
                selections = [
                    part for part in (_stringify_pdf_object(item) for item in resolved_value) if part
                ]
                value_text = ", ".join(selections) if selections else None
            else:
                value_text = _stringify_pdf_object(resolved_value)
        elif field_type_lower == "sig":
            kind = "signature"
            value_text = _stringify_pdf_object(resolved_value)
        else:
            continue

        form_field = FormField(
            bbox=bbox,
            field_type=kind,
            name=field_name,
            label=label,
            value=value_text,
            checked=checked,
            options=options,
            tooltip=tooltip,
            read_only=read_only,
            multiline=multiline,
        )
        fields.append(form_field)

    return fields


def _extract_annotations(page: DictionaryObject) -> list[PdfAnnotation]:
    annotations = _resolve_indirect(page.get(NameObject("/Annots")))
    if not isinstance(annotations, ArrayObject):
        return []
    results: list[PdfAnnotation] = []
    for entry in annotations:
        annot = _resolve_indirect(entry)
        if not isinstance(annot, DictionaryObject):
            continue
        subtype = annot.get(NameObject("/Subtype"))
        subtype_name = str(subtype)
        if subtype_name not in {"/Text", "Text", "/FreeText", "FreeText"}:
            continue
        rect = _resolve_indirect(annot.get(NameObject("/Rect")))
        if not isinstance(rect, ArrayObject) or len(rect) < 4:
            continue
        try:
            left, bottom, right, top = [float(rect[i]) for i in range(4)]
        except Exception:
            continue
        text_obj = _resolve_indirect(annot.get(NameObject("/Contents")))
        author_obj = _resolve_indirect(annot.get(NameObject("/T")))
        text = str(text_obj) if isinstance(text_obj, TextStringObject) else None
        author = str(author_obj) if isinstance(author_obj, TextStringObject) else None
        bbox = BoundingBox(
            left=min(left, right),
            bottom=min(bottom, top),
            right=max(left, right),
            top=max(bottom, top),
        )
        results.append(
            PdfAnnotation(
                bbox=bbox,
                text=text,
                author=author,
                subtype=subtype_name[1:] if subtype_name.startswith("/") else subtype_name,
            )
        )
    return results


def extract_outline(reader: PdfReader) -> list[OutlineNode]:
    """Return a normalised outline tree for *reader* if present."""

    try:
        raw_outline = getattr(reader, "outline", None)
    except AttributeError:
        raw_outline = None
    except Exception:
        raw_outline = None
    if not raw_outline:
        try:
            raw_outline = getattr(reader, "outlines", None)
        except Exception:
            raw_outline = None
    if not raw_outline:
        return []

    seen: set[str] = set()

    def walk(entries: object) -> list[OutlineNode]:
        nodes: list[OutlineNode] = []
        last_node: OutlineNode | None = None
        if isinstance(entries, (list, ArrayObject)):
            iterable = list(entries)
        else:
            iterable = [entries]
        for entry in iterable:
            resolved = _resolve_indirect(entry)
            if isinstance(resolved, (list, ArrayObject)):
                if last_node is not None:
                    last_node.children.extend(walk(resolved))
                continue
            node = _outline_node_from_entry(reader, resolved, seen)
            if node is None:
                continue
            nodes.append(node)
            last_node = node
        return nodes

    outline_nodes = walk(raw_outline)
    return outline_nodes


def _outline_node_from_entry(
    reader: PdfReader, entry: object | None, seen: set[str]
) -> OutlineNode | None:
    entry = _resolve_indirect(entry)
    title: str | None = None
    anchor: str | None = None
    page_index: int | None = None
    top: float | None = None

    if isinstance(entry, Destination):
        title = entry.title or "Untitled"
        anchor, page_index, top = _resolve_destination(reader, entry)
    elif isinstance(entry, DictionaryObject):
        title_obj = entry.get(NameObject("/Title"))
        if isinstance(title_obj, TextStringObject):
            title = str(title_obj)
        elif title_obj is not None:
            title = str(title_obj)
        dest = entry.get(NameObject("/Dest"))
        if dest is None:
            action = entry.get(NameObject("/A"))
            action = _resolve_indirect(action)
            if isinstance(action, DictionaryObject):
                dest = action.get(NameObject("/D"))
        if dest is not None:
            anchor, page_index, top = _resolve_destination(reader, dest)
    elif isinstance(entry, TextStringObject):
        title = str(entry)
    elif isinstance(entry, str):
        title = entry

    if title is None:
        return None
    title = title.strip() or "Untitled"

    if anchor:
        base = anchor
        counter = 1
        while anchor in seen:
            anchor = f"{base}_{counter}"
            counter += 1
        seen.add(anchor)

    return OutlineNode(
        title=title,
        page_number=page_index,
        top=top,
        anchor=anchor,
    )


def capture_text_fragments(
    page: DictionaryObject,
    reader: PdfReader,
    state: ContentStreamState | None = None,
    font_maps: Mapping[int, tuple[dict[str, str], int]] | None = None,
) -> list[CapturedText]:
    fragments: list[CapturedText] = []
    if isinstance(font_maps, Mapping):
        translation_maps: dict[int, tuple[dict[str, str], int]] = {}
        for key, value in font_maps.items():
            try:
                dict_id = int(key)
            except Exception:
                continue
            if (
                isinstance(value, tuple)
                and len(value) == 2
                and isinstance(value[0], Mapping)
            ):
                mapping = dict(value[0])
                max_key_length_raw = value[1]
                if isinstance(max_key_length_raw, (int, float)):
                    max_key_length = int(max_key_length_raw)
                else:
                    max_key_length = 1
                translation_maps[dict_id] = (mapping, max(1, max_key_length))
        if not translation_maps:
            translation_maps = font_translation_maps(page)
    else:
        translation_maps = font_translation_maps(page)
    try:
        content = ContentStream(page.get_contents(), reader)
    except Exception:
        if state is not None:
            state.reset()
        return []

    resources = page.get(NameObject("/Resources"))
    fonts_dict = None
    if isinstance(resources, DictionaryObject):
        fonts_dict = resources.get(NameObject("/Font"))

    working_state = state or ContentStreamState()
    working_state.reset()

    def _rgb_tuple_to_hex(color: tuple[float, float, float]) -> str:
        r = int(round(max(0.0, min(color[0], 1.0)) * 255))
        g = int(round(max(0.0, min(color[1], 1.0)) * 255))
        b = int(round(max(0.0, min(color[2], 1.0)) * 255))
        return f"{r:02X}{g:02X}{b:02X}"

    matrix_stack: list[tuple[float, float, float, float, float, float]] = [
        working_state.IDENTITY_MATRIX
    ]
    text_matrix: tuple[float, float, float, float, float, float] | None = (
        working_state.IDENTITY_MATRIX
    )
    line_matrix: tuple[float, float, float, float, float, float] | None = (
        working_state.IDENTITY_MATRIX
    )
    current_font_ref: NameObject | None = None
    current_font_size: float | None = None
    current_fill_color: tuple[float, float, float] = (0.0, 0.0, 0.0)
    current_stroke_color: tuple[float, float, float] = (0.0, 0.0, 0.0)
    character_spacing = 0.0
    word_spacing = 0.0
    horizontal_scaling = 100.0
    leading = 0.0
    text_objects = 0
    max_stack_depth = 1

    def _resolve_font(n: NameObject | None) -> DictionaryObject | None:
        if n is None or not isinstance(fonts_dict, DictionaryObject):
            return None
        try:
            ref = fonts_dict.get(n)
            if isinstance(ref, IndirectObject):
                return ref.get_object()
            if isinstance(ref, DictionaryObject):
                return ref
        except Exception:
            return None
        return None

    def _emit_text(raw: str) -> None:
        nonlocal text_matrix, current_font_ref, current_font_size
        if not raw:
            return
        tm = text_matrix or working_state.IDENTITY_MATRIX
        combined = _matrix_multiply(matrix_stack[-1], tm)
        x, y = _matrix_apply(combined, 0.0, 0.0)
        font_obj = _resolve_font(current_font_ref)
        base_font = None
        if isinstance(font_obj, DictionaryObject):
            base_font_obj = font_obj.get(NameObject("/BaseFont"))
            if base_font_obj is not None:
                base_font = str(base_font_obj)
                if base_font.startswith("/"):
                    base_font = base_font[1:]
            mapping_entry = translation_maps.get(id(font_obj))
            if mapping_entry is not None:
                mapping, max_key_length = mapping_entry
                raw = apply_translation_map(raw, mapping, max_key_length)
        vertical = False
        if _is_vertical_matrix(list(tm)) and is_east_asian_text(raw):
            vertical = True
        a, b, c, d, _e, _f = combined
        try:
            sx = (a * a + b * b) ** 0.5
            sy = (c * c + d * d) ** 0.5
            scale = sy if vertical and sy > 0 else sx if sx > 0 else max(sx, sy)
            eff_font_size = float(current_font_size) * scale if current_font_size else None
        except Exception:
            eff_font_size = float(current_font_size) if current_font_size else None
        color_hex = _rgb_tuple_to_hex(current_fill_color)
        fragments.append(
            CapturedText(
                text=raw,
                x=float(x),
                y=float(y),
                font_name=str(base_font) if base_font is not None else None,
                font_size=eff_font_size,
                vertical=vertical,
                color=color_hex,
            )
        )
        working_state.last_text_position = (float(x), float(y))
        if base_font is not None:
            working_state.font_name = base_font

    operations = getattr(content, "operations", [])
    for operands, operator in operations:
        op = operator
        if op == b"q":
            matrix_stack.append(matrix_stack[-1])
            if len(matrix_stack) > max_stack_depth:
                max_stack_depth = len(matrix_stack)
        elif op == b"Q":
            if len(matrix_stack) > 1:
                matrix_stack.pop()
        elif op == b"cm" and len(operands) == 6:
            try:
                matrix = tuple(float(value) for value in operands)
                matrix_stack[-1] = _matrix_multiply(matrix_stack[-1], matrix)
            except Exception:
                pass
        elif op == b"BT":
            text_matrix = working_state.IDENTITY_MATRIX
            line_matrix = text_matrix
            text_objects += 1
        elif op == b"ET":
            text_matrix = None
            line_matrix = None
        elif op == b"Tf" and len(operands) >= 2:
            try:
                current_font_ref = operands[0]
                current_font_size = float(operands[1])
            except Exception:
                current_font_ref = None
                current_font_size = None
        elif op == b"Tm" and len(operands) >= 6:
            try:
                tm = tuple(float(operands[i]) for i in range(6))
                text_matrix = tm
                line_matrix = tm
            except Exception:
                pass
        elif op in {b"Td", b"TD"} and len(operands) >= 2:
            if line_matrix is None:
                continue
            try:
                tx = float(operands[0])
                ty = float(operands[1])
                translate = (1.0, 0.0, 0.0, 1.0, tx, ty)
                line_matrix = _matrix_multiply(line_matrix, translate)
                text_matrix = line_matrix
            except Exception:
                pass
        elif op == b"T*":
            if line_matrix is None:
                continue
            try:
                ty = -1.2 * (current_font_size or 12.0)
                translate = (1.0, 0.0, 0.0, 1.0, 0.0, ty)
                line_matrix = _matrix_multiply(line_matrix, translate)
                text_matrix = line_matrix
            except Exception:
                pass
        elif op == b"Tc" and operands:
            try:
                character_spacing = float(operands[0])
            except Exception:
                character_spacing = character_spacing
        elif op == b"Tw" and operands:
            try:
                word_spacing = float(operands[0])
            except Exception:
                word_spacing = word_spacing
        elif op == b"Tz" and operands:
            try:
                horizontal_scaling = float(operands[0])
            except Exception:
                horizontal_scaling = horizontal_scaling
        elif op == b"TL" and operands:
            try:
                leading = float(operands[0])
            except Exception:
                leading = leading
        elif op == b"Tj" and operands:
            s = operands[0]
            try:
                raw = s if isinstance(s, str) else s.decode("latin1", "ignore")
            except Exception:
                raw = str(s)
            _emit_text(raw)
        elif op == b"TJ" and operands:
            arr = operands[0]
            parts: list[str] = []
            for item in arr:
                if isinstance(item, (bytes, bytearray)):
                    try:
                        parts.append(item.decode("latin1", "ignore"))
                    except Exception:
                        parts.append(str(item))
                elif isinstance(item, str):
                    parts.append(item)
            if parts:
                _emit_text("".join(parts))
        elif op == b"RG" and len(operands) >= 3:
            try:
                current_stroke_color = _rgb_color(operands[:3])
            except Exception:
                pass
        elif op in {b"rg", b"sc", b"scn"} and len(operands) >= 3:
            try:
                r = float(operands[0])
                g = float(operands[1])
                b = float(operands[2])
                maxv = max(r, g, b)
                if maxv > 1.0:
                    r /= maxv
                    g /= maxv
                    b /= maxv
                current_fill_color = (max(0.0, min(r, 1.0)), max(0.0, min(g, 1.0)), max(0.0, min(b, 1.0)))
            except Exception:
                pass
        elif op == b"g" and operands:
            try:
                v = float(operands[0])
                if v > 1.0:
                    v = 1.0
                if v < 0.0:
                    v = 0.0
                current_fill_color = (v, v, v)
            except Exception:
                pass
        elif op == b"k" and len(operands) >= 4:
            try:
                c = float(operands[0])
                m = float(operands[1])
                yv = float(operands[2])
                kv = float(operands[3])
                r = 1.0 - min(1.0, c + kv)
                g = 1.0 - min(1.0, m + kv)
                b = 1.0 - min(1.0, yv + kv)
                current_fill_color = (r, g, b)
            except Exception:
                pass
        elif op == b"G" and operands:
            try:
                v = float(operands[0])
                v = max(0.0, min(v, 1.0))
                current_stroke_color = (v, v, v)
            except Exception:
                pass
        elif op == b"K" and len(operands) >= 4:
            try:
                current_stroke_color = _cmyk_color(operands[:4])
            except Exception:
                pass
        elif op in {b"SC", b"SCN"} and operands:
            generic = _generic_color(operands)
            if generic is not None:
                current_stroke_color = generic

    working_state.ctm = matrix_stack[-1]
    working_state.text_matrix = text_matrix or working_state.IDENTITY_MATRIX
    working_state.line_matrix = line_matrix or working_state.IDENTITY_MATRIX
    working_state.font_ref = current_font_ref
    working_state.font_size = current_font_size
    working_state.fill_color = current_fill_color
    working_state.stroke_color = current_stroke_color
    working_state.character_spacing = character_spacing
    working_state.word_spacing = word_spacing
    working_state.horizontal_scaling = horizontal_scaling
    working_state.leading = leading
    working_state.text_objects = text_objects
    working_state.graphics_stack_depth = len(matrix_stack)
    working_state.max_graphics_stack_depth = max_stack_depth

    if state is None:
        # Ensure standalone calls leave the state with a sensible default font name.
        font_obj = _resolve_font(current_font_ref)
        if isinstance(font_obj, DictionaryObject):
            base_font_obj = font_obj.get(NameObject("/BaseFont"))
            if base_font_obj is not None:
                base_font = str(base_font_obj)
                if base_font.startswith("/"):
                    base_font = base_font[1:]
                working_state.font_name = base_font

    return fragments


def extract_vector_graphics(page: DictionaryObject, reader: PdfReader) -> tuple[list[Line], list[Path]]:
    try:
        content = ContentStream(page.get_contents(), reader)
    except Exception:
        return [], []

    lines: list[Line] = []
    paths: list[Path] = []
    state_stack: list[_GraphicsState] = [_GraphicsState()]
    matrix_stack: list[tuple[float, float, float, float, float, float]] = [
        (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    ]
    current_path: list[list[tuple[float, float]]] = []
    current_point: tuple[float, float] | None = None
    ext_states = _load_ext_gstates(page, reader)

    def move_to(x: float, y: float) -> None:
        nonlocal current_point
        transformed = _matrix_apply(matrix_stack[-1], x, y)
        current_path.append([transformed])
        current_point = transformed

    def line_to(x: float, y: float) -> None:
        nonlocal current_point
        if not current_path:
            move_to(x, y)
            return
        transformed = _matrix_apply(matrix_stack[-1], x, y)
        current_path[-1].append(transformed)
        current_point = transformed

    def curve_to(x1: float, y1: float, x2: float, y2: float, x3: float, y3: float) -> None:
        nonlocal current_point
        if current_point is None:
            move_to(x3, y3)
            return
        p0 = current_point
        p1 = _matrix_apply(matrix_stack[-1], x1, y1)
        p2 = _matrix_apply(matrix_stack[-1], x2, y2)
        p3 = _matrix_apply(matrix_stack[-1], x3, y3)
        if not current_path:
            current_path.append([p0])
        points = _approximate_cubic(p0, p1, p2, p3)
        current_path[-1].extend(points[1:])
        current_point = p3

    def close_path() -> None:
        nonlocal current_point
        if not current_path:
            return
        subpath = current_path[-1]
        if not subpath:
            return
        if subpath[0] != subpath[-1]:
            subpath.append(subpath[0])
        current_point = subpath[0]

    def append_rectangle(x: float, y: float, width: float, height: float) -> None:
        nonlocal current_point
        x2 = x + width
        y2 = y + height
        p0 = _matrix_apply(matrix_stack[-1], x, y)
        p1 = _matrix_apply(matrix_stack[-1], x2, y)
        p2 = _matrix_apply(matrix_stack[-1], x2, y2)
        p3 = _matrix_apply(matrix_stack[-1], x, y2)
        current_path.append([p0, p1, p2, p3, p0])
        current_point = p0

    def finalise(stroke: bool, fill: bool, evenodd: bool, state: _GraphicsState) -> None:
        nonlocal current_path, current_point
        flattened = [list(sub) for sub in current_path if len(sub) >= 2]
        if not flattened:
            current_path = []
            current_point = None
            return
        is_rectangle = _path_is_rectangle(flattened)
        if stroke and not fill and _path_is_line(flattened):
            sub = flattened[0]
            start = sub[0]
            end = sub[-1]
            if start == end and len(sub) >= 2:
                end = sub[-2]
            lines.append(Line(start=start, end=end, stroke_width=state.line_width))
            current_path = []
            current_point = None
            return
        if stroke and is_rectangle:
            corners = flattened[0]
            for start, end in zip(corners, corners[1:]):
                lines.append(Line(start=start, end=end, stroke_width=state.line_width))
            if not fill:
                current_path = []
                current_point = None
                return
        if not fill and not stroke:
            current_path = []
            current_point = None
            return
        stroke_color = state.stroke_color if stroke else None
        fill_color = state.fill_color if fill else None
        if not stroke_color and not fill_color:
            current_path = []
            current_point = None
            return
        paths.append(
            Path(
                subpaths=[list(sub) for sub in flattened],
                stroke_color=stroke_color,
                fill_color=fill_color,
                stroke_width=state.line_width if stroke else None,
                fill_rule="evenodd" if evenodd else "nonzero",
                stroke_alpha=state.stroke_alpha,
                fill_alpha=state.fill_alpha,
                is_rectangle=is_rectangle,
            )
        )
        current_path = []
        current_point = None

    operations = getattr(content, "operations", [])
    for operands, operator in operations:
        state = state_stack[-1]
        if operator == b"q":
            state_stack.append(state.clone())
            matrix_stack.append(matrix_stack[-1])
        elif operator == b"Q":
            if len(state_stack) > 1:
                state_stack.pop()
                matrix_stack.pop()
        elif operator == b"cm" and len(operands) == 6:
            matrix = tuple(float(value) for value in operands)
            matrix_stack[-1] = _matrix_multiply(matrix_stack[-1], matrix)
        elif operator == b"w" and operands:
            state.line_width = float(operands[0])
        elif operator == b"RG" and len(operands) >= 3:
            state.stroke_color = _rgb_color(operands)
        elif operator == b"rg" and len(operands) >= 3:
            state.fill_color = _rgb_color(operands)
        elif operator == b"G" and operands:
            state.stroke_color = _gray_color(operands)
        elif operator == b"g" and operands:
            state.fill_color = _gray_color(operands)
        elif operator == b"K" and len(operands) >= 4:
            state.stroke_color = _cmyk_color(operands)
        elif operator == b"k" and len(operands) >= 4:
            state.fill_color = _cmyk_color(operands)
        elif operator in {b"SC", b"SCN"} and operands:
            generic = _generic_color(operands)
            if generic is not None:
                state.stroke_color = generic
        elif operator in {b"sc", b"scn"} and operands:
            generic = _generic_color(operands)
            if generic is not None:
                state.fill_color = generic
        elif operator == b"gs" and operands:
            name = _clean_name(operands[0])
            ext = ext_states.get(name)
            if isinstance(ext, DictionaryObject):
                stroke_alpha = ext.get(NameObject("/CA"))
                fill_alpha = ext.get(NameObject("/ca"))
                if stroke_alpha is not None:
                    state.stroke_alpha = max(0.0, min(_to_float(stroke_alpha), 1.0))
                if fill_alpha is not None:
                    state.fill_alpha = max(0.0, min(_to_float(fill_alpha), 1.0))
        elif operator == b"m" and len(operands) >= 2:
            move_to(float(operands[0]), float(operands[1]))
        elif operator == b"l" and len(operands) >= 2:
            line_to(float(operands[0]), float(operands[1]))
        elif operator == b"c" and len(operands) >= 6:
            curve_to(
                float(operands[0]),
                float(operands[1]),
                float(operands[2]),
                float(operands[3]),
                float(operands[4]),
                float(operands[5]),
            )
        elif operator == b"h":
            close_path()
        elif operator == b"re" and len(operands) >= 4:
            append_rectangle(
                float(operands[0]),
                float(operands[1]),
                float(operands[2]),
                float(operands[3]),
            )
        elif operator in {b"S", b"s", b"f", b"F", b"f*", b"B", b"B*", b"b", b"b*"}:
            if operator in {b"s", b"b", b"b*"}:
                close_path()
            stroke = operator in {b"S", b"s", b"B", b"B*", b"b", b"b*"}
            fill = operator in {b"f", b"F", b"f*", b"B", b"B*", b"b", b"b*"}
            evenodd = operator in {b"f*", b"B*", b"b*"}
            finalise(stroke, fill, evenodd, state.clone())
        elif operator == b"n":
            current_path = []
            current_point = None

    return lines, paths


def page_from_reader(
    page: DictionaryObject,
    roles: Iterable[str],
    index: int,
    *,
    strip_whitespace: bool,
    reader: PdfReader,
) -> Page:
    captured = capture_text_fragments(page, reader)
    text_blocks = text_fragments_to_blocks(
        captured,
        page_width=float(page.mediabox.width),
        page_height=float(page.mediabox.height),
        roles=list(roles),
        strip_whitespace=strip_whitespace,
    )
    images = extract_page_images(page, reader)
    lines, paths = extract_vector_graphics(page, reader)
    links = _extract_links(page, reader)
    annotations = _extract_annotations(page)
    form_fields = _extract_form_fields(page)
    return Page(
        number=index,
        width=float(page.mediabox.width),
        height=float(page.mediabox.height),
        text_blocks=text_blocks,
        images=images,
        lines=lines,
        paths=paths,
        links=links,
        annotations=annotations,
        form_fields=form_fields,
        tagged_roles=list(roles),
    )


def extract_struct_roles(reader: PdfReader) -> tuple[Mapping[int, list[str]], list[str], bool]:
    try:
        catalog = reader.trailer[NameObject("/Root")]
    except KeyError:
        return {}, [], False
    if not isinstance(catalog, DictionaryObject):
        return {}, [], False
    struct_tree_obj = catalog.get(NameObject("/StructTreeRoot"))
    if not isinstance(struct_tree_obj, (DictionaryObject, IndirectObject)):
        return {}, [], False

    def resolve(node: object | None) -> object | None:
        if isinstance(node, IndirectObject):
            try:
                return node.get_object()
            except Exception:
                return None
        return node

    struct_tree = resolve(struct_tree_obj)
    if not isinstance(struct_tree, DictionaryObject):
        return {}, [], False

    page_refs: dict[int, int] = {}
    page_objects: dict[int, int] = {}
    pages: list[DictionaryObject] = []
    for index, page in enumerate(reader.pages):
        ref = getattr(page, "indirect_reference", None)
        if isinstance(ref, IndirectObject):
            page_refs[ref.idnum] = index
        page_objects[id(page)] = index
        pages.append(page)

    roles_by_page: dict[int, list[str]] = defaultdict(list)
    global_roles: list[str] = []

    def walk(node: object | None) -> None:
        node = resolve(node)
        if isinstance(node, DictionaryObject):
            role = node.get(NameObject("/S"))
            page_ref = node.get(NameObject("/Pg"))
            if role is not None:
                page_index: int | None = None
                resolved_page: object | None = None
                if isinstance(page_ref, IndirectObject):
                    page_index = page_refs.get(page_ref.idnum)
                    if page_index is None:
                        resolved_page = resolve(page_ref)
                else:
                    resolved_page = resolve(page_ref)
                if page_index is None and isinstance(resolved_page, DictionaryObject):
                    page_index = page_objects.get(id(resolved_page))
                    if page_index is None:
                        for candidate_index, candidate_page in enumerate(pages):
                            if resolved_page is candidate_page or resolved_page == candidate_page:
                                page_index = candidate_index
                                break
                role_name = str(role)
                clean_role = role_name[1:] if role_name.startswith("/") else role_name
                if page_index is not None:
                    roles_by_page[page_index].append(clean_role)
                else:
                    global_roles.append(clean_role)
            children = resolve(node.get(NameObject("/K")))
            if isinstance(children, ArrayObject):
                for child in children:
                    walk(child)
            elif children is not None:
                walk(children)
        elif isinstance(node, ArrayObject):
            for child in node:
                walk(child)
        elif isinstance(node, IndirectObject):
            walk(resolve(node))

    walk(struct_tree.get(NameObject("/K")))
    is_tagged = bool(global_roles or roles_by_page or struct_tree)
    return roles_by_page, global_roles, is_tagged


def _load_ext_gstates(
    page: DictionaryObject, reader: PdfReader
) -> dict[str, DictionaryObject]:
    resources = _resolve_indirect(page.get(NameObject("/Resources")))
    if not isinstance(resources, DictionaryObject):
        return {}
    ext = _resolve_indirect(resources.get(NameObject("/ExtGState")))
    if not isinstance(ext, DictionaryObject):
        return {}
    result: dict[str, DictionaryObject] = {}
    for name_obj, entry in ext.items():
        name = _clean_name(name_obj)
        resolved = _resolve_indirect(entry)
        if isinstance(resolved, DictionaryObject):
            result[name] = resolved
    return result


def _clean_name(name: object) -> str:
    raw = str(name)
    return raw[1:] if raw.startswith("/") else raw


def _to_float(value: object) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except Exception:
        return 0.0


def _rgb_color(values: Sequence[object]) -> tuple[float, float, float]:
    comps = [_to_float(v) for v in values[:3]]
    max_value = max(comps or [0.0])
    if max_value > 1.0:
        scale = 255.0 if max_value > 10.0 else max_value
        if scale:
            comps = [component / scale for component in comps]
    return tuple(max(0.0, min(component, 1.0)) for component in comps)


def _gray_color(values: Sequence[object]) -> tuple[float, float, float]:
    if not values:
        return (0.0, 0.0, 0.0)
    value = _to_float(values[0])
    if value > 1.0:
        value = value / (255.0 if value > 10.0 else value)
    value = max(0.0, min(value, 1.0))
    return (value, value, value)


def _cmyk_color(values: Sequence[object]) -> tuple[float, float, float]:
    comps = [_to_float(v) for v in values[:4]]
    max_value = max(comps or [0.0])
    if max_value > 1.0:
        scale = 255.0 if max_value > 10.0 else max_value
        if scale:
            comps = [component / scale for component in comps]
    c, m, y, k = (max(0.0, min(component, 1.0)) for component in comps + [0.0] * (4 - len(comps)))
    r = 1.0 - min(1.0, c + k)
    g = 1.0 - min(1.0, m + k)
    b = 1.0 - min(1.0, y + k)
    return (r, g, b)


def _generic_color(values: Sequence[object]) -> tuple[float, float, float] | None:
    if not values:
        return None
    count = len(values)
    if count == 1:
        return _gray_color(values)
    if count == 3:
        return _rgb_color(values)
    if count >= 4:
        return _cmyk_color(values)
    return None


def _approximate_cubic(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    steps: int = 12,
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    if steps <= 0:
        steps = 1
    for index in range(steps + 1):
        t = index / steps
        points.append(_cubic_point(p0, p1, p2, p3, t))
    return points


def _cubic_point(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    t: float,
) -> tuple[float, float]:
    mt = 1.0 - t
    x = (
        (mt ** 3) * p0[0]
        + 3 * (mt ** 2) * t * p1[0]
        + 3 * mt * (t ** 2) * p2[0]
        + (t ** 3) * p3[0]
    )
    y = (
        (mt ** 3) * p0[1]
        + 3 * (mt ** 2) * t * p1[1]
        + 3 * mt * (t ** 2) * p2[1]
        + (t ** 3) * p3[1]
    )
    return (x, y)


def _matrix_multiply(
    lhs: tuple[float, float, float, float, float, float],
    rhs: tuple[float, float, float, float, float, float],
) -> tuple[float, float, float, float, float, float]:
    a1, b1, c1, d1, e1, f1 = lhs
    a2, b2, c2, d2, e2, f2 = rhs
    return (
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1,
        b1 * e2 + d1 * f2 + f1,
    )


def _matrix_apply(
    matrix: tuple[float, float, float, float, float, float],
    x: float,
    y: float,
) -> tuple[float, float]:
    a, b, c, d, e, f = matrix
    return a * x + c * y + e, b * x + d * y + f


def _path_is_line(subpaths: list[list[tuple[float, float]]]) -> bool:
    if len(subpaths) != 1:
        return False
    sub = subpaths[0]
    if len(sub) == 2:
        return sub[0] != sub[1]
    if len(sub) == 3 and sub[0] == sub[-1]:
        return sub[0] != sub[1]
    return False


def _path_is_rectangle(subpaths: list[list[tuple[float, float]]]) -> bool:
    if len(subpaths) != 1:
        return False
    sub = subpaths[0]
    if len(sub) < 4:
        return False
    points = sub[:-1] if len(sub) > 1 and sub[0] == sub[-1] else sub
    if len(points) != 4:
        return False
    xs = {round(point[0], 2) for point in points}
    ys = {round(point[1], 2) for point in points}
    return len(xs) == 2 and len(ys) == 2
