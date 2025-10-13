"""Numbering helpers for DOCX generation."""

from __future__ import annotations

from typing import Dict, List

__all__ = ["NUMBERING_SCHEMES", "NUMBERING_IDS", "PUNCTUATION_MARKERS", "ordered_level_formats"]

_ORDERED_LEVEL_FORMATS: Dict[str, List[str]] = {
    "decimal": [
        "decimal",
        "lowerLetter",
        "lowerRoman",
        "decimal",
        "lowerLetter",
        "lowerRoman",
        "decimal",
        "lowerLetter",
        "lowerRoman",
    ],
    "lowerLetter": [
        "lowerLetter",
        "lowerRoman",
        "decimal",
        "lowerLetter",
        "lowerRoman",
        "decimal",
        "lowerLetter",
        "lowerRoman",
        "decimal",
    ],
    "upperLetter": [
        "upperLetter",
        "upperRoman",
        "decimal",
        "upperLetter",
        "upperRoman",
        "decimal",
        "upperLetter",
        "upperRoman",
        "decimal",
    ],
    "lowerRoman": [
        "lowerRoman",
        "decimal",
        "lowerLetter",
        "lowerRoman",
        "decimal",
        "lowerLetter",
        "lowerRoman",
        "decimal",
        "lowerLetter",
    ],
    "upperRoman": [
        "upperRoman",
        "decimal",
        "upperLetter",
        "upperRoman",
        "decimal",
        "upperLetter",
        "upperRoman",
        "decimal",
        "upperLetter",
    ],
}

PUNCTUATION_MARKERS = {
    "dot": ("", "."),
    "paren": ("", ")"),
    "enclosed": ("(", ")"),
}


def _generate_numbering_schemes() -> tuple[list[tuple[int, str, str | None, str | None]], dict[tuple[str, str | None, str | None], int]]:
    schemes: list[tuple[int, str, str | None, str | None]] = []
    mapping: dict[tuple[str, str | None, str | None], int] = {}
    next_id = 1
    schemes.append((next_id, "bullet", None, None))
    mapping[("bullet", None, None)] = next_id
    next_id += 1
    for format_name in _ORDERED_LEVEL_FORMATS:
        for punctuation in PUNCTUATION_MARKERS:
            key = ("ordered", format_name, punctuation)
            schemes.append((next_id, key[0], key[1], key[2]))
            mapping[key] = next_id
            next_id += 1
    return schemes, mapping


NUMBERING_SCHEMES, NUMBERING_IDS = _generate_numbering_schemes()


def ordered_level_formats(format_name: str) -> List[str]:
    return _ORDERED_LEVEL_FORMATS.get(format_name, _ORDERED_LEVEL_FORMATS["decimal"])
