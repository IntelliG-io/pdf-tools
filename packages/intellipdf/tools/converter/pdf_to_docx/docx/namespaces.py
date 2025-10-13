"""Namespace configuration and XML constants for DOCX generation."""

from __future__ import annotations

from datetime import datetime, timezone
from xml.etree.ElementTree import register_namespace

__all__ = [
    "XML_NS",
    "DEFAULT_TIMESTAMP",
    "EMU_PER_POINT",
    "TWIPS_PER_POINT",
]

XML_NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "dcmitype": "http://purl.org/dc/dcmitype/",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    "ep": "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties",
    "vt": "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
}

for prefix, uri in XML_NS.items():
    register_namespace(prefix, uri)

DEFAULT_TIMESTAMP = datetime(2023, 1, 1, tzinfo=timezone.utc)
EMU_PER_POINT = 12700
TWIPS_PER_POINT = 20
