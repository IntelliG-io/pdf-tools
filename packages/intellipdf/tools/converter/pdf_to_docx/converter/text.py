"""Text utilities used throughout the converter."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean

from ..primitives import BoundingBox, TextBlock
from .constants import (
    CJK_RANGES,
    HALFWIDTH_KATAKANA_RANGE,
    HANGUL_SYLLABLE_RANGE,
    HIRAGANA_RANGE,
    KATAKANA_RANGE,
    LIGATURE_TRANSLATION,
    RTL_RANGES,
)

__all__ = [
    "CapturedText",
    "font_traits",
    "infer_language",
    "indent_level",
    "is_rtl_text",
    "normalise_text_content",
    "text_fragments_to_blocks",
    "is_east_asian_text",
]

EAST_ASIAN_RANGES = CJK_RANGES + (
    HIRAGANA_RANGE,
    KATAKANA_RANGE,
    HALFWIDTH_KATAKANA_RANGE,
    HANGUL_SYLLABLE_RANGE,
)
KANA_RANGES = (HIRAGANA_RANGE, KATAKANA_RANGE, HALFWIDTH_KATAKANA_RANGE)


@dataclass(slots=True)
class CapturedText:
    text: str
    x: float
    y: float
    font_name: str | None
    font_size: float | None
    vertical: bool = False


def normalise_text_content(text: str, *, strip: bool) -> str:
    cleaned = text.replace("\u00ad", "")
    cleaned = cleaned.translate(LIGATURE_TRANSLATION)
    if strip:
        cleaned = cleaned.strip()
    return cleaned


def is_rtl_text(text: str) -> bool:
    for char in text:
        code = ord(char)
        for start, end in RTL_RANGES:
            if start <= code <= end:
                return True
    return False


def _code_in_ranges(code: int, ranges: tuple[tuple[int, int], ...]) -> bool:
    for start, end in ranges:
        if start <= code <= end:
            return True
    return False


def _contains_range(text: str, ranges: tuple[tuple[int, int], ...]) -> bool:
    return any(_code_in_ranges(ord(char), ranges) for char in text)


def is_east_asian_text(text: str) -> bool:
    return any(_code_in_ranges(ord(char), EAST_ASIAN_RANGES) for char in text)


def infer_language(text: str) -> str | None:
    if not text:
        return None
    if is_rtl_text(text):
        if any("\u05d0" <= ch <= "\u05ea" for ch in text):
            return "he-IL"
        return "ar-SA"
    if _contains_range(text, (HANGUL_SYLLABLE_RANGE,)):
        return "ko-KR"
    if _contains_range(text, KANA_RANGES):
        return "ja-JP"
    if _contains_range(text, CJK_RANGES):
        return "zh-CN"
    if any(ord(ch) > 0x0400 for ch in text):
        return "und"
    return "en-US"


def font_traits(font_name: str | None) -> tuple[bool, bool, bool]:
    if not font_name:
        return False, False, False
    upper = font_name.upper()
    bold = any(keyword in upper for keyword in ("BOLD", "BLACK", "HEAVY"))
    italic = any(keyword in upper for keyword in ("ITALIC", "OBLIQUE"))
    underline = "UNDERLINE" in upper or "UL" in upper
    return bold, italic, underline


def indent_level(block: TextBlock, section) -> float:  # type: ignore[override]
    return max(0.0, block.bbox.left - section.margin_left)


def text_fragments_to_blocks(
    fragments: list[CapturedText],
    *,
    page_width: float,
    page_height: float,
    roles: list[str],
    strip_whitespace: bool,
) -> list[TextBlock]:
    role_iter = iter(roles)
    if not fragments:
        bbox = BoundingBox(0.0, 0.0, page_width, page_height)
        return [
            TextBlock(
                text="",
                bbox=bbox,
                font_name=None,
                font_size=None,
                role=next(role_iter, None),
            )
        ]

    sorted_fragments = sorted(fragments, key=lambda item: (-item.y, item.x))
    horizontal_lines: list[list[CapturedText]] = []
    vertical_columns: list[list[CapturedText]] = []

    for fragment in sorted_fragments:
        if fragment.vertical:
            placed = False
            for column in vertical_columns:
                center = fmean(item.x for item in column)
                threshold = (fragment.font_size or 12.0) * 0.8
                if abs(fragment.x - center) <= threshold:
                    column.append(fragment)
                    placed = True
                    break
            if not placed:
                vertical_columns.append([fragment])
            continue

        placed = False
        for line in horizontal_lines:
            baseline = fmean(item.y for item in line)
            if abs(fragment.y - baseline) <= (fragment.font_size or 12.0) * 0.6:
                line.append(fragment)
                placed = True
                break
        if not placed:
            horizontal_lines.append([fragment])

    blocks: list[TextBlock] = []

    for line in horizontal_lines:
        line.sort(key=lambda item: item.x)
        text_parts: list[str] = []
        last_x = float("-inf")
        for fragment in line:
            text = normalise_text_content(fragment.text, strip=strip_whitespace)
            if not text:
                continue
            if last_x != float("-inf"):
                gap = fragment.x - last_x
                threshold = (fragment.font_size or 10.0) * 0.6
                if gap > threshold:
                    text_parts.append(" ")
            text_parts.append(text)
            advance = (fragment.font_size or 10.0) * max(len(fragment.text), 1) * 0.5
            last_x = fragment.x + advance

        combined = "".join(text_parts)
        if not combined or not combined.strip():
            continue
        min_x = min(item.x for item in line)
        font_size = next((item.font_size for item in line if item.font_size), None)
        font_name = next((item.font_name for item in line if item.font_name), None)
        block_height = font_size or 12.0
        bold, italic, underline = font_traits(font_name)
        text_language = infer_language(combined)
        rtl = is_rtl_text(combined)
        baseline = fmean(item.y for item in line)
        superscript = all((item.y - baseline) > (item.font_size or block_height) * 0.3 for item in line)
        subscript = all((baseline - item.y) > (item.font_size or block_height) * 0.3 for item in line)
        bbox = BoundingBox(
            left=min_x,
            bottom=min(item.y for item in line) - block_height,
            right=max(item.x for item in line) + block_height,
            top=max(item.y for item in line),
        )
        blocks.append(
            TextBlock(
                text=combined,
                bbox=bbox,
                font_name=font_name,
                font_size=font_size,
                bold=bold,
                italic=italic,
                underline=underline,
                color="000000",
                rtl=rtl,
                language=text_language,
                superscript=superscript,
                subscript=subscript,
            )
        )

    for column in vertical_columns:
        column.sort(key=lambda item: item.y, reverse=True)
        text_parts: list[str] = []
        last_y: float | None = None
        for fragment in column:
            text = normalise_text_content(fragment.text, strip=strip_whitespace)
            if not text:
                continue
            if last_y is not None:
                gap = last_y - fragment.y
                threshold = (fragment.font_size or 10.0) * 0.9
                if gap > threshold * 2.2:
                    text_parts.append("\n")
            text_parts.append(text)
            last_y = fragment.y

        combined = "".join(text_parts)
        if not combined or not combined.strip():
            continue
        font_size = next((item.font_size for item in column if item.font_size), None)
        font_name = next((item.font_name for item in column if item.font_name), None)
        bold, italic, underline = font_traits(font_name)
        text_language = infer_language(combined)
        rtl = is_rtl_text(combined)
        min_x = min(item.x for item in column)
        max_x = max(item.x for item in column)
        min_y = min(item.y for item in column)
        max_y = max(item.y for item in column)
        block_size = font_size or 12.0
        bbox = BoundingBox(
            left=min_x - block_size * 0.5,
            bottom=min_y - block_size,
            right=max_x + block_size * 0.5,
            top=max_y + block_size * 0.5,
        )
        blocks.append(
            TextBlock(
                text=combined,
                bbox=bbox,
                font_name=font_name,
                font_size=font_size,
                bold=bold,
                italic=italic,
                underline=underline,
                color="000000",
                rtl=rtl,
                language=text_language,
                superscript=False,
                subscript=False,
                vertical=True,
            )
        )

    blocks.sort(key=lambda block: (-block.bbox.top, block.bbox.left))
    for block in blocks:
        block.role = block.role or next(role_iter, None)
    return blocks
