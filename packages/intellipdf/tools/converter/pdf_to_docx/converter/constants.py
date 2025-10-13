"""Shared constants for the PDF to DOCX converter pipeline."""

from __future__ import annotations

import re

__all__ = [
    "ANNOTATION_ROLES",
    "BULLET_PATTERN",
    "DECIMAL_PATTERN",
    "ROMAN_PATTERN",
    "ALPHA_PATTERN",
    "PDF_DATE_PREFIX",
    "END_PUNCTUATION",
    "LIGATURE_TRANSLATION",
    "RTL_RANGES",
    "CJK_RANGES",
    "HIRAGANA_RANGE",
    "KATAKANA_RANGE",
    "HALFWIDTH_KATAKANA_RANGE",
    "HANGUL_SYLLABLE_RANGE",
]

BULLET_PATTERN = re.compile(r"^(?P<marker>[•‣◦▪⁃–—·∙\-*])\s+")
DECIMAL_PATTERN = re.compile(r"^(?P<marker>\(?\d+(?:[\.)]|\)))\s+")
ROMAN_PATTERN = re.compile(r"^(?P<marker>\(?[ivxlcdmIVXLCDM]+(?:[\.)]|\)))\s+")
ALPHA_PATTERN = re.compile(r"^(?P<marker>\(?[a-zA-Z]+(?:[\.)]|\)))\s+")
PDF_DATE_PREFIX = "D:"
ANNOTATION_ROLES = {"ANNOT", "ANNOTATION", "NOTE", "COMMENT"}
END_PUNCTUATION = {".", "!", "?"}
LIGATURE_TRANSLATION = str.maketrans(
    {
        "ﬁ": "fi",
        "ﬂ": "fl",
        "ﬃ": "ffi",
        "ﬄ": "ffl",
        "ﬀ": "ff",
        "ﬅ": "st",
        "ﬆ": "st",
    }
)
RTL_RANGES = (
    (0x0590, 0x08FF),
    (0xFB1D, 0xFDFF),
    (0xFE70, 0xFEFC),
)

CJK_RANGES = (
    (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF),
    (0xF900, 0xFAFF),
    (0x20000, 0x2A6DF),
    (0x2A700, 0x2B73F),
    (0x2B740, 0x2B81F),
    (0x2B820, 0x2CEAF),
    (0x2CEB0, 0x2EBEF),
)

HIRAGANA_RANGE = (0x3040, 0x309F)
KATAKANA_RANGE = (0x30A0, 0x30FF)
HALFWIDTH_KATAKANA_RANGE = (0xFF66, 0xFF9F)
HANGUL_SYLLABLE_RANGE = (0xAC00, 0xD7AF)
