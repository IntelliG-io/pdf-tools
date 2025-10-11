"""High-level DOCX package writer."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from ..ir import Annotation, BlockElement, Document, DocumentMetadata, Paragraph, Picture, Shape, Table
from .elements import (
    build_comments_xml,
    build_document_xml,
    build_endnotes_xml,
    build_footnotes_xml,
)
from .namespaces import DEFAULT_TIMESTAMP
from .parts import (
    build_app_properties_xml,
    build_content_types_xml,
    build_core_properties_xml,
    build_document_relationships_xml,
    build_numbering_xml,
    build_root_relationships_xml,
    build_styles_xml,
)
from .relationships import RelationshipManager
from .types import CoreProperties, DocumentStatistics
from .validation import (
    DOCX_ZIP_TIMESTAMP,
    validate_content_types_document,
    validate_relationship_targets,
    validate_xml_parts,
)

__all__ = ["write_docx"]


def _document_metadata_to_core(metadata: DocumentMetadata, tagged: bool) -> CoreProperties:
    title = metadata.title or ("Tagged PDF" if tagged else "PDF Conversion")
    creator = metadata.author or "pdf2docx"
    description = metadata.description
    subject = metadata.subject
    keywords = ", ".join(metadata.keywords) if metadata.keywords else None
    created = metadata.created or DEFAULT_TIMESTAMP
    modified = metadata.modified or created
    revision = metadata.revision or None
    if revision is not None:
        revision = str(revision)
    return CoreProperties(
        title=title,
        creator=creator,
        description=description,
        subject=subject,
        keywords=keywords,
        last_modified_by=metadata.last_modified_by or creator,
        created=created,
        modified=modified,
        language=metadata.language,
        revision=revision,
    )


def _iter_paragraphs(elements: Iterable[BlockElement]) -> Iterable[Paragraph]:
    for element in elements:
        if isinstance(element, Paragraph):
            yield element
        elif isinstance(element, Annotation):
            yield element.as_paragraph()
        elif isinstance(element, Shape):
            yield element.as_paragraph()
        elif isinstance(element, Picture):
            continue
        elif isinstance(element, Table):
            for row in element.rows:
                for cell in row.cells:
                    yield from _iter_paragraphs(cell.content)


def _compute_statistics(document: Document) -> DocumentStatistics:
    stats = DocumentStatistics()
    for section in document.iter_sections():
        for paragraph in _iter_paragraphs(section.iter_elements()):
            stats.update_from_paragraph(paragraph.text())
    stats.update_from_document(document.page_count or len(list(document.iter_sections())))
    return stats


def _normalise_bytes(data: bytes | bytearray | str) -> bytes:
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)
    if isinstance(data, str):
        return data.encode("utf-8")
    raise TypeError(f"Unsupported payload type: {type(data)!r}")


def _zipinfo(name: str) -> ZipInfo:
    info = ZipInfo(name)
    info.date_time = DOCX_ZIP_TIMESTAMP
    info.compress_type = ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    return info


def write_docx(document: Document, output_path: Path) -> DocumentStatistics:
    """Write *document* to ``output_path`` and return collected statistics."""

    output_path = output_path.resolve()
    relationships = RelationshipManager()
    document_xml = build_document_xml(document, relationships)
    styles_xml = build_styles_xml()
    numbering_xml = build_numbering_xml()
    stats = _compute_statistics(document)
    core_properties = build_core_properties_xml(
        _document_metadata_to_core(document.metadata, document.tagged_pdf)
    )
    app_properties = build_app_properties_xml(stats)
    if document.footnotes:
        footnotes_xml = build_footnotes_xml(document.footnotes, relationships)
        relationships.register_part(
            part_name="footnotes.xml",
            data=footnotes_xml,
            relationship_type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footnotes",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml",
        )
    if document.endnotes:
        endnotes_xml = build_endnotes_xml(document.endnotes, relationships)
        relationships.register_part(
            part_name="endnotes.xml",
            data=endnotes_xml,
            relationship_type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/endnotes",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.endnotes+xml",
        )
    if document.comments:
        comments_xml = build_comments_xml(document.comments, relationships)
        relationships.register_part(
            part_name="comments.xml",
            data=comments_xml,
            relationship_type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml",
        )
    document_relationships = build_document_relationships_xml(relationships)
    root_relationships = build_root_relationships_xml()
    media_parts = list(relationships.iter_media())
    media_defaults: list[tuple[str, str]] = []
    for part_name, _data, mime in media_parts:
        suffix = Path(part_name).suffix.lstrip(".").lower()
        if suffix and mime:
            media_defaults.append((suffix, mime))

    xml_parts = list(relationships.iter_parts())
    validate_relationship_targets(relationships, xml_parts, media_parts)
    overrides = [
        (part_name, content_type)
        for part_name, _, content_type in xml_parts
        if content_type is not None
    ]
    content_types = build_content_types_xml(media_defaults, overrides)
    validate_content_types_document(content_types, overrides, media_defaults)

    xml_payloads = [
        ("word/document.xml", document_xml),
        ("word/styles.xml", styles_xml),
        ("word/numbering.xml", numbering_xml),
        ("docProps/core.xml", core_properties),
        ("docProps/app.xml", app_properties),
        ("word/_rels/document.xml.rels", document_relationships),
        ("_rels/.rels", root_relationships),
        ("[Content_Types].xml", content_types),
    ]
    for part_name, data, _ in xml_parts:
        xml_payloads.append((f"word/{part_name}", data))
    validate_xml_parts(xml_payloads)

    with ZipFile(output_path, "w", compression=ZIP_DEFLATED) as archive:
        for name, data in xml_payloads:
            archive.writestr(_zipinfo(name), _normalise_bytes(data))
        for part_name, data, _ in media_parts:
            archive.writestr(_zipinfo(f"word/{part_name}"), _normalise_bytes(data))

    return stats
