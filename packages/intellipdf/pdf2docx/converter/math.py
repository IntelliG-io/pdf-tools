"""Math extraction and conversion helpers for the PDF → DOCX pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Set
from xml.etree import ElementTree

from ..docx.namespaces import XML_NS
from ..ir import Equation
from ..primitives import BoundingBox, Image, Line, TextBlock
from .images import image_to_picture, lines_to_picture

__all__ = [
    "EquationDetectionResult",
    "block_is_equation",
    "block_to_equation",
    "mathml_to_omml",
    "text_to_omml",
]


MATH_ROLES = {"FORMULA", "MATH", "EQUATION"}


@dataclass(slots=True)
class EquationDetectionResult:
    """Outcome describing how an equation was captured."""

    equation: Equation
    used_image_index: int | None = None


def block_is_equation(block: TextBlock) -> bool:
    """Return ``True`` if *block* represents a mathematical formula."""

    if not block.role:
        return False
    return block.role.upper() in MATH_ROLES


def block_to_equation(
    block: TextBlock,
    images: Sequence[Image],
    used_images: Set[int],
    candidate_lines: Sequence[Line],
) -> EquationDetectionResult:
    """Convert a tagged math text block into an :class:`Equation` instance."""

    alt_text = (block.text or "").strip() or "Equation"
    mathml = _extract_mathml(block.text)
    omml = None
    if mathml:
        omml = mathml_to_omml(mathml)
    if omml is None and block.text and block.text.strip():
        omml = text_to_omml(block.text.strip())

    picture = None
    chosen_index: int | None = None
    for index, image in enumerate(images):
        if index in used_images:
            continue
        overlap = _bbox_intersection_ratio(block.bbox, image.bbox)
        if overlap >= 0.25:
            picture = image_to_picture(image)
            chosen_index = index
            break

    if picture is None and omml is None:
        relevant_lines = [
            line
            for line in candidate_lines
            if _bbox_intersection_ratio(block.bbox, _line_bbox(line)) >= 0.5
        ]
        if relevant_lines:
            picture = lines_to_picture(relevant_lines, block.bbox)

    description = alt_text or "Equation"
    if picture is not None:
        picture.description = description
        if not picture.name:
            picture.name = "equation"

    equation = Equation(
        omml=omml,
        mathml=mathml,
        picture=picture,
        text=(block.text or "").strip() or None,
        description=description,
        bbox=(block.bbox.left, block.bbox.bottom, block.bbox.right, block.bbox.top),
    )
    equation.metadata = {
        "bbox_top": f"{block.bbox.top:.2f}",
        "bbox_bottom": f"{block.bbox.bottom:.2f}",
        "bbox_left": f"{block.bbox.left:.2f}",
        "bbox_right": f"{block.bbox.right:.2f}",
    }
    return EquationDetectionResult(equation=equation, used_image_index=chosen_index)


def mathml_to_omml(mathml: str) -> str | None:
    """Convert a MathML string into a minimal OMML representation."""

    try:
        root = ElementTree.fromstring(mathml)
    except ElementTree.ParseError:
        return None

    text = _mathml_to_text(root).strip()
    if not text:
        text = "".join(root.itertext()).strip()
    if not text:
        return None
    return text_to_omml(text)


def text_to_omml(expression: str) -> str:
    """Wrap a linearised expression into an ``m:oMathPara`` element."""

    m_ns = XML_NS["m"]
    o_math_para = ElementTree.Element(f"{{{m_ns}}}oMathPara")
    o_math = ElementTree.SubElement(o_math_para, f"{{{m_ns}}}oMath")
    run = ElementTree.SubElement(o_math, f"{{{m_ns}}}r")
    text = ElementTree.SubElement(run, f"{{{m_ns}}}t")
    text.text = expression
    return ElementTree.tostring(o_math_para, encoding="unicode")


def _extract_mathml(content: str | None) -> str | None:
    if not content:
        return None
    snippet = content.strip()
    if "<math" not in snippet:
        return None
    start = snippet.find("<math")
    if start == -1:
        return None
    return snippet[start:]


def _mathml_to_text(node: ElementTree.Element) -> str:
    tag = _local_name(node.tag)
    children = list(node)
    if tag in {"math", "mrow"}:
        return "".join(_mathml_to_text(child) for child in children)
    if tag in {"mi", "mn", "mo", "mtext"}:
        return "".join(node.itertext())
    if tag == "msup" and len(children) >= 2:
        return f"{_mathml_to_text(children[0])}^({_mathml_to_text(children[1])})"
    if tag == "msub" and len(children) >= 2:
        return f"{_mathml_to_text(children[0])}_({_mathml_to_text(children[1])})"
    if tag == "msubsup" and len(children) >= 3:
        base = _mathml_to_text(children[0])
        sub = _mathml_to_text(children[1])
        sup = _mathml_to_text(children[2])
        return f"{base}_({sub})^({sup})"
    if tag == "mfrac" and len(children) >= 2:
        num = _mathml_to_text(children[0])
        den = _mathml_to_text(children[1])
        return f"({num})/({den})"
    if tag == "msqrt" and children:
        return f"sqrt({_mathml_to_text(children[0])})"
    if tag == "mfenced" and children:
        open_delim = node.get("open", "(")
        close_delim = node.get("close", ")")
        separators = node.get("separators", ",")
        parts = [_mathml_to_text(child) for child in children]
        return f"{open_delim}{separators.join(parts)}{close_delim}"
    return "".join(_mathml_to_text(child) for child in children) or "".join(node.itertext())


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _bbox_intersection_ratio(a: BoundingBox, b: BoundingBox) -> float:
    left = max(a.left, b.left)
    right = min(a.right, b.right)
    bottom = max(a.bottom, b.bottom)
    top = min(a.top, b.top)
    width = max(0.0, right - left)
    height = max(0.0, top - bottom)
    if width <= 0.0 or height <= 0.0:
        return 0.0
    area = (a.right - a.left) * (a.top - a.bottom)
    if area <= 0:
        return 0.0
    return (width * height) / max(area, 1.0)


def _line_bbox(line: Line) -> BoundingBox:
    return BoundingBox(
        left=min(line.start[0], line.end[0]),
        bottom=min(line.start[1], line.end[1]),
        right=max(line.start[0], line.end[0]),
        top=max(line.start[1], line.end[1]),
    )

