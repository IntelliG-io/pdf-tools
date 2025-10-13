"""Packaging-level regression tests for the DOCX writer."""

from base64 import b64decode
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

import pytest

from packages.intellipdf.tools.converter.pdf_to_docx.docx import write_docx
from packages.intellipdf.tools.converter.pdf_to_docx.docx.namespaces import XML_NS
from packages.intellipdf.tools.converter.pdf_to_docx.docx.parts import build_content_types_xml
from packages.intellipdf.tools.converter.pdf_to_docx.docx.relationships import RelationshipManager
from packages.intellipdf.tools.converter.pdf_to_docx.docx.validation import (
    DOCX_ZIP_TIMESTAMP,
    validate_content_types_document,
    validate_relationship_targets,
    validate_xml_parts,
)
from packages.intellipdf.tools.converter.pdf_to_docx.ir import (
    Comment,
    Document,
    DocumentMetadata,
    Footnote,
    Paragraph,
    Picture,
    Run,
    Section,
)


def _build_section(elements: list) -> Section:
    return Section(page_width=612.0, page_height=792.0, elements=elements)


def _basic_document(elements: list) -> Document:
    metadata = DocumentMetadata(title="Basic Document", author="Tester")
    section = _build_section(elements)
    return Document(metadata=metadata, sections=[section], page_count=1)


def test_docx_package_contains_required_parts(tmp_path: Path) -> None:
    paragraph = Paragraph(runs=[Run(text="Hello world")])
    document = _basic_document([paragraph])

    output_path = tmp_path / "basic.docx"
    stats = write_docx(document, output_path)

    assert output_path.exists(), "DOCX archive was not created"
    assert stats.pages == 1

    required_entries = {
        "[Content_Types].xml",
        "_rels/.rels",
        "docProps/core.xml",
        "docProps/app.xml",
        "word/document.xml",
        "word/styles.xml",
        "word/numbering.xml",
        "word/_rels/document.xml.rels",
    }

    with ZipFile(output_path) as archive:
        names = set(archive.namelist())

    missing = required_entries - names
    assert not missing, f"Missing DOCX parts: {sorted(missing)}"


PNG_BYTES = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQI12P4//8/AwAI/AL+XwH0yQAAAABJRU5ErkJggg=="
)


def test_docx_package_registers_media_and_optional_parts(tmp_path: Path) -> None:
    paragraph = Paragraph(runs=[Run(text="Paragraph with footnote")])
    picture = Picture(data=PNG_BYTES, width=72.0, height=72.0, mime_type="image/png", name="figure")

    footnote = Footnote(id=1, paragraphs=[Paragraph(runs=[Run(text="Footnote body")])])
    comment = Comment(id=2, paragraphs=[Paragraph(runs=[Run(text="Comment text")])], author="Editor")

    document = Document(
        metadata=DocumentMetadata(title="With Media", author="Tester"),
        sections=[_build_section([paragraph, picture])],
        page_count=1,
        footnotes=[footnote],
        comments=[comment],
    )

    output_path = tmp_path / "extended.docx"
    write_docx(document, output_path)

    with ZipFile(output_path) as archive:
        names = set(archive.namelist())
        assert "word/footnotes.xml" in names
        assert "word/comments.xml" in names

        media_entries = {name for name in names if name.startswith("word/media/")}
        assert media_entries, "Media assets were not written"

        rels_xml = ET.fromstring(archive.read("word/_rels/document.xml.rels"))
        rel_ids = [rel.attrib["Id"] for rel in rels_xml]
        assert rel_ids == [f"rId{i}" for i in range(1, len(rel_ids) + 1)]

        internal_targets = {
            rel.attrib["Target"]
            for rel in rels_xml
            if rel.attrib.get("TargetMode") != "External"
        }
        for target in internal_targets:
            assert f"word/{target}" in names

        content_types_xml = ET.fromstring(archive.read("[Content_Types].xml"))
        ns = {"ct": "http://schemas.openxmlformats.org/package/2006/content-types"}
        defaults = {
            (elem.attrib["Extension"], elem.attrib["ContentType"])
            for elem in content_types_xml.findall("ct:Default", ns)
        }
        assert ("png", "image/png") in defaults

        overrides = {
            elem.attrib["PartName"]
            for elem in content_types_xml.findall("ct:Override", ns)
        }
        assert "/word/footnotes.xml" in overrides
        assert "/word/comments.xml" in overrides

        root_relationships = ET.fromstring(archive.read("_rels/.rels"))
        root_targets = {rel.attrib["Target"] for rel in root_relationships}
        assert {
            "word/document.xml",
            "docProps/core.xml",
            "docProps/app.xml",
        } <= root_targets


def test_styles_define_core_hierarchy(tmp_path: Path) -> None:
    paragraph = Paragraph(runs=[Run(text="Styled paragraph")])
    document = _basic_document([paragraph])

    output_path = tmp_path / "styles.docx"
    write_docx(document, output_path)

    with ZipFile(output_path) as archive:
        styles_xml = ET.fromstring(archive.read("word/styles.xml"))

    w = f"{{{XML_NS['w']}}}"
    style_nodes = {
        node.attrib[f"{w}styleId"]: node for node in styles_xml.findall(f"{w}style")
    }

    required_styles = {
        "Normal",
        "Heading1",
        "Heading2",
        "Heading3",
        "ListParagraph",
        "Quote",
        "Caption",
        "Code",
        "Title",
        "Subtitle",
        "Hyperlink",
    }
    assert required_styles <= set(style_nodes), "Missing expected style definitions"

    def _based_on(style_id: str) -> str | None:
        node = style_nodes[style_id]
        based_on = node.find(f"{w}basedOn")
        if based_on is None:
            return None
        return based_on.attrib.get(f"{w}val")

    for style_id in ["Heading1", "Heading2", "Heading3", "ListParagraph", "Quote", "Caption", "Code", "Title", "Subtitle"]:
        assert _based_on(style_id) == "Normal"

    assert _based_on("Hyperlink") == "DefaultParagraphFont"

    normal_spacing = style_nodes["Normal"].find(f"{w}pPr/{w}spacing")
    assert normal_spacing is not None
    assert normal_spacing.attrib.get(f"{w}before") == "0"
    assert normal_spacing.attrib.get(f"{w}after") == "160"
    assert normal_spacing.attrib.get(f"{w}line") == "240"

    heading_props = style_nodes["Heading1"].find(f"{w}pPr")
    assert heading_props is not None
    assert heading_props.find(f"{w}keepNext") is not None
    assert heading_props.find(f"{w}keepLines") is not None

    list_props = style_nodes["ListParagraph"].find(f"{w}pPr")
    assert list_props is not None
    list_indent = list_props.find(f"{w}ind")
    assert list_indent is not None
    assert list_indent.attrib.get(f"{w}left") == "720"
    assert list_indent.attrib.get(f"{w}hanging") == "360"

    quote_indent = style_nodes["Quote"].find(f"{w}pPr/{w}ind")
    assert quote_indent is not None
    assert quote_indent.attrib.get(f"{w}left") == "720"
    assert quote_indent.attrib.get(f"{w}right") == "720"


def test_write_docx_is_deterministic(tmp_path: Path) -> None:
    paragraph = Paragraph(runs=[Run(text="Deterministic content")])
    document = _basic_document([paragraph])

    path_a = tmp_path / "deterministic_a.docx"
    path_b = tmp_path / "deterministic_b.docx"

    write_docx(document, path_a)
    write_docx(document, path_b)

    assert path_a.read_bytes() == path_b.read_bytes(), "DOCX output should be reproducible"

    with ZipFile(path_a) as archive:
        for info in archive.infolist():
            assert info.date_time == DOCX_ZIP_TIMESTAMP


def test_validate_relationship_targets_detects_issues() -> None:
    manager = RelationshipManager()
    manager._relationships.append(("rId3", "type", "styles.xml", None))
    manager._relationships.append(("rId5", "type", "numbering.xml", None))

    with pytest.raises(ValueError):
        validate_relationship_targets(manager, [], [])

    manager = RelationshipManager()
    manager._relationships.append(("rId3", "type", "missing.xml", None))

    with pytest.raises(ValueError):
        validate_relationship_targets(manager, [], [])


def test_validate_content_types_document_detects_mismatch() -> None:
    media_defaults = [("png", "image/png")]
    overrides = [
        ("footnotes.xml", "application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"),
    ]
    content_types = build_content_types_xml(media_defaults, overrides)
    tampered = content_types.replace(b"/word/footnotes.xml", b"/word/footnotes-missing.xml")

    with pytest.raises(ValueError):
        validate_content_types_document(tampered, overrides, media_defaults)


def test_validate_xml_parts_rejects_invalid_payload() -> None:
    with pytest.raises(ValueError):
        validate_xml_parts([("word/document.xml", b"<w:document>")])
