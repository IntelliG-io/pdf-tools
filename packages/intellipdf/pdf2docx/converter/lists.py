"""List and numbering helpers."""

from __future__ import annotations

from ..ir import Numbering, Section
from ..primitives import TextBlock
from .constants import ALPHA_PATTERN, BULLET_PATTERN, DECIMAL_PATTERN, END_PUNCTUATION, ROMAN_PATTERN
from .text import indent_level

__all__ = [
    "normalise_text_for_numbering",
    "should_continue_across_pages",
]


def normalise_text_for_numbering(block: TextBlock | str, section: Section | None) -> tuple[str, Numbering | None]:
    if isinstance(block, TextBlock):
        text = block.text
        role = block.role.upper() if block.role else None
        indent = indent_level(block, section) if section is not None else 0.0
    else:
        text = str(block)
        role = None
        indent = 0.0
    working = text.lstrip()
    prefix_len = len(text) - len(working)
    numbering: Numbering | None = None
    if role in {"LI", "LBODY", "LBL", "L"}:
        numbering = Numbering(kind="bullet", level=0, indent=indent)
    match = BULLET_PATTERN.match(working)
    if match:
        marker = match.group("marker")
        numbering = Numbering(kind="bullet", level=0, marker=marker, indent=indent)
        working = working[match.end() :]
    else:
        match_decimal = DECIMAL_PATTERN.match(working)
        if match_decimal:
            marker = match_decimal.group("marker")
            punctuation = "dot"
            if marker.startswith("(") and marker.endswith(")"):
                punctuation = "enclosed"
            elif marker.endswith(")"):
                punctuation = "paren"
            numbering = Numbering(
                kind="ordered",
                level=0,
                format="decimal",
                punctuation=punctuation,
                marker=marker,
                indent=indent,
            )
            working = working[match_decimal.end() :]
        else:
            match_roman = ROMAN_PATTERN.match(working)
            if match_roman:
                marker = match_roman.group("marker")
                punctuation = "dot"
                if marker.startswith("(") and marker.endswith(")"):
                    punctuation = "enclosed"
                elif marker.endswith(")"):
                    punctuation = "paren"
                format_kind = "upperRoman" if marker.strip("().").isupper() else "lowerRoman"
                numbering = Numbering(
                    kind="ordered",
                    level=0,
                    format=format_kind,
                    punctuation=punctuation,
                    marker=marker,
                    indent=indent,
                )
                working = working[match_roman.end() :]
            else:
                match_alpha = ALPHA_PATTERN.match(working)
                if match_alpha:
                    marker = match_alpha.group("marker")
                    punctuation = "dot"
                    if marker.startswith("(") and marker.endswith(")"):
                        punctuation = "enclosed"
                    elif marker.endswith(")"):
                        punctuation = "paren"
                    stripped = marker.strip("().")
                    format_kind = "upperLetter" if stripped.isupper() else "lowerLetter"
                    numbering = Numbering(
                        kind="ordered",
                        level=0,
                        format=format_kind,
                        punctuation=punctuation,
                        marker=marker,
                        indent=indent,
                    )
                    working = working[match_alpha.end() :]
    cleaned = text[:prefix_len] + working
    return (cleaned if cleaned else text), numbering


def should_continue_across_pages(text: str, role: str | None) -> bool:
    stripped = text.rstrip()
    if not stripped:
        return False
    if role and role.upper().startswith("H"):
        return False
    if stripped.endswith(("-", "–", "—")):
        return True
    return stripped[-1] not in END_PUNCTUATION
