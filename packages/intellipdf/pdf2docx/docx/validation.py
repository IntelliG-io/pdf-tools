"""Validation helpers for DOCX package generation."""

from __future__ import annotations

from typing import Iterable, Sequence
from xml.etree.ElementTree import ParseError, fromstring

from .namespaces import DEFAULT_TIMESTAMP
from .relationships import RelationshipManager

__all__ = [
    "DOCX_ZIP_TIMESTAMP",
    "validate_content_types_document",
    "validate_relationship_targets",
    "validate_xml_parts",
]

DOCX_ZIP_TIMESTAMP = (
    DEFAULT_TIMESTAMP.year,
    DEFAULT_TIMESTAMP.month,
    DEFAULT_TIMESTAMP.day,
    DEFAULT_TIMESTAMP.hour,
    DEFAULT_TIMESTAMP.minute,
    DEFAULT_TIMESTAMP.second,
)


def validate_xml_parts(parts: Iterable[tuple[str, bytes]]) -> None:
    """Ensure each XML payload is well-formed."""

    for name, payload in parts:
        try:
            fromstring(payload)
        except ParseError as exc:
            raise ValueError(f"Generated XML for {name!r} is not well-formed: {exc}.") from exc


def validate_relationship_targets(
    relationships: RelationshipManager,
    xml_parts: Sequence[tuple[str, bytes, str | None]],
    media_parts: Sequence[tuple[str, bytes, str]],
) -> None:
    """Verify that relationship targets refer to known package parts."""

    available_targets = {"styles.xml", "numbering.xml"}
    available_targets.update(part_name for part_name, *_ in xml_parts)
    available_targets.update(part_name for part_name, *_ in media_parts)

    seen_ids: set[str] = set()
    seen_numbers: list[int] = []

    for rid, _type, target, mode in relationships.iter_relationships():
        if rid in seen_ids:
            raise ValueError(f"Duplicate relationship identifier detected: {rid}.")
        seen_ids.add(rid)
        if rid.startswith("rId") and rid[3:].isdigit():
            seen_numbers.append(int(rid[3:]))
        if mode == "External":
            continue
        if target not in available_targets:
            raise ValueError(
                f"Relationship {rid} references missing part {target!r}."
            )

    if seen_numbers:
        seen_numbers.sort()
        expected = list(range(seen_numbers[0], seen_numbers[0] + len(seen_numbers)))
        if seen_numbers != expected:
            raise ValueError("Relationship identifiers are not sequential.")


def validate_content_types_document(
    content_types_xml: bytes,
    overrides: Sequence[tuple[str, str]],
    media_defaults: Sequence[tuple[str, str]],
) -> None:
    """Ensure ``[Content_Types].xml`` aligns with registered parts."""

    root = fromstring(content_types_xml)
    ns = {"ct": "http://schemas.openxmlformats.org/package/2006/content-types"}

    defaults = {
        (elem.attrib["Extension"].lower(), elem.attrib["ContentType"])
        for elem in root.findall("ct:Default", ns)
    }
    required_defaults = {
        ("rels", "application/vnd.openxmlformats-package.relationships+xml"),
        ("xml", "application/xml"),
    }
    for ext, mime in media_defaults:
        if ext:
            required_defaults.add((ext.lower(), mime))
    if not required_defaults <= defaults:
        missing = required_defaults - defaults
        raise ValueError(
            "[Content_Types].xml is missing required default declarations: "
            f"{sorted(missing)}."
        )

    overrides_in_xml = {
        (elem.attrib["PartName"], elem.attrib["ContentType"])
        for elem in root.findall("ct:Override", ns)
    }
    required_overrides = {
        ("/word/document.xml", "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"),
        ("/word/styles.xml", "application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"),
        ("/word/numbering.xml", "application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"),
        ("/docProps/core.xml", "application/vnd.openxmlformats-package.core-properties+xml"),
        ("/docProps/app.xml", "application/vnd.openxmlformats-officedocument.extended-properties+xml"),
    }
    required_overrides.update((f"/word/{name}", content_type) for name, content_type in overrides)

    if required_overrides != overrides_in_xml:
        missing = required_overrides - overrides_in_xml
        extra = overrides_in_xml - required_overrides
        messages = []
        if missing:
            messages.append(f"missing overrides {sorted(missing)}")
        if extra:
            messages.append(f"unexpected overrides {sorted(extra)}")
        raise ValueError("[Content_Types].xml overrides mismatch: " + ", ".join(messages))
