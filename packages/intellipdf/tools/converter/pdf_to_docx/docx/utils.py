"""Utility helpers for DOCX XML generation."""

from __future__ import annotations

from xml.etree.ElementTree import Element, tostring

from .namespaces import EMU_PER_POINT, TWIPS_PER_POINT

__all__ = ["serialize", "twips", "emus"]


def serialize(element: Element) -> bytes:
    return tostring(element, encoding="utf-8", xml_declaration=True)


def twips(value: float) -> int:
    return int(round(value * TWIPS_PER_POINT))


def emus(value: float) -> int:
    return int(round(value * EMU_PER_POINT))
