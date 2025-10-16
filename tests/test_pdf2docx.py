from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from xml.etree import ElementTree

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject,
    DictionaryObject,
    IndirectObject,
    NameObject,
    NumberObject,
    StreamObject,
)

from intellipdf import ConversionMetadata, ConversionOptions, convert_document
from intellipdf.converter import ConversionPipeline
from intellipdf.tools.converter.pdf_to_docx.converter import PdfToDocxConverter
from intellipdf.tools.converter.pdf_to_docx.converter import (
    _DocumentBuilder,
    _apply_translation_map,
    _blocks_to_paragraphs_static,
    _font_translation_maps,
    _normalise_text_for_numbering,
    _parse_pdf_date,
)
from intellipdf.tools.converter.pdf_to_docx.converter.pipeline import PIPELINE_STEPS
from intellipdf.tools.converter.pdf_to_docx.converter.math import block_to_equation, mathml_to_omml
from intellipdf.tools.converter.pdf_to_docx.converter.reader import (
    _is_vertical_matrix,
    extract_vector_graphics,
)
from intellipdf.tools.converter.pdf_to_docx.converter.text import CapturedText, text_fragments_to_blocks
from intellipdf.tools.common.interfaces import ConversionContext
from intellipdf.tools.converter.pdf_to_docx.ir import (
    Document as IRDocument,
    DocumentMetadata,
    Equation,
    Paragraph as IRParagraph,
    Run as IRRun,
    Section as IRSection,
)
from intellipdf.tools.converter.pdf_to_docx.docx.elements import BookmarkState, build_equation_paragraph
from intellipdf.tools.converter.pdf_to_docx.docx.namespaces import XML_NS
from intellipdf.tools.converter.pdf_to_docx.docx.relationships import RelationshipManager
from intellipdf.tools.converter.pdf_to_docx.primitives import (
    BoundingBox,
    FormField,
    Image,
    Line,
    Link,
    Page,
    PdfAnnotation,
    PdfDocument,
    Path,
    OutlineNode,
    TextBlock,
)
from intellipdf.tools.converter.pdf_to_docx.converter.images import path_to_picture
from intellipdf.tools.converter.pdf_to_docx.converter.layout import collect_page_placements
from intellipdf.tools.converter.pdf_to_docx.docx import write_docx


def _png_bytes(width: int, height: int, color: tuple[int, int, int, int] = (255, 0, 0, 255)) -> bytes:
    import struct
    import zlib

    signature = b"\x89PNG\r\n\x1a\n"
    if len(color) != 4:
        raise ValueError("color must have four components")
    row = bytes([0] + list(color) * width)
    payload = zlib.compress(row * height)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = chunk(
        b"IHDR",
        struct.pack(
            ">IIBBBBB",
            width,
            height,
            8,
            6,
            0,
            0,
            0,
        ),
    )
    idat = chunk(b"IDAT", payload)
    iend = chunk(b"IEND", b"")
    return signature + ihdr + idat + iend
def _create_pdf(
    path: Path,
    text: str,
    metadata: dict[str, str] | None = None,
    *,
    password: str | None = None,
) -> None:
    writer = PdfWriter()
    page = writer.add_blank_page(width=200, height=200)

    font_dict = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_ref = writer._add_object(font_dict)
    resources = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})})
    page[NameObject("/Resources")] = resources

    content_bytes = f"BT /F1 12 Tf 72 100 Td ({text}) Tj ET".encode("utf-8")
    stream = StreamObject()
    stream[NameObject("/Length")] = NumberObject(len(content_bytes))
    stream._data = content_bytes
    stream_ref = writer._add_object(stream)
    page[NameObject("/Contents")] = stream_ref

    if metadata:
        writer.add_metadata(metadata)

    if password:
        writer.encrypt(password)

    with path.open("wb") as fh:
        writer.write(fh)


def _assert_pipeline_log(result) -> None:
    assert len(result.log) == len(PIPELINE_STEPS)
    assert result.log[0].startswith("Load or receive parsed PdfDocument instance.")
    assert result.log[-1].startswith("Return success status and summary log")
    assert any("Extracted" in entry for entry in result.log), "Expected extraction details in log"
    assert any("cross-reference" in entry.lower() for entry in result.log)


@pytest.mark.parametrize("text", ["Hello PDF", "Multi\nLine PDF"])
def test_pdf_to_docx_conversion(tmp_path: Path, text: str) -> None:
    pdf_path = tmp_path / "input.pdf"
    _create_pdf(pdf_path, text)

    docx_path = tmp_path / "output.docx"
    result = convert_document(pdf_path, docx_path)

    assert result.output_path == docx_path.resolve()
    assert result.page_count == 1
    assert result.paragraph_count >= 1
    assert result.word_count >= 2
    _assert_pipeline_log(result)

    with ZipFile(docx_path) as archive:
        with archive.open("word/document.xml") as handle:
            root = ElementTree.parse(handle).getroot()
        assert "word/styles.xml" in archive.namelist()

    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    texts = [
        (node.text or "")
        for node in root.findall(".//w:body/w:p/w:r/w:t", namespace)
    ]
    combined_text = " ".join(texts)
    for token in text.replace("\n", " ").split():
        assert token in combined_text


def test_pdf_to_docx_encrypted_requires_password(tmp_path: Path) -> None:
    pdf_path = tmp_path / "encrypted.pdf"
    _create_pdf(pdf_path, "Secret PDF", password="letmein")

    with pytest.raises(ValueError, match="requires a password"):
        convert_document(pdf_path, tmp_path / "encrypted.docx")


def test_pdf_to_docx_encrypted_with_password(tmp_path: Path) -> None:
    pdf_path = tmp_path / "encrypted.pdf"
    _create_pdf(pdf_path, "Secret PDF", password="letmein")

    docx_path = tmp_path / "encrypted.docx"
    options = ConversionOptions(password="letmein")
    result = convert_document(pdf_path, docx_path, options=options)

    assert result.output_path == docx_path.resolve()
    assert result.page_count == 1
    _assert_pipeline_log(result)


def test_conversion_pipeline_records_cross_reference(tmp_path: Path) -> None:
    pdf_path = tmp_path / "xref.pdf"
    _create_pdf(pdf_path, "CrossRef")

    docx_path = tmp_path / "xref.docx"
    context = ConversionContext()
    pipeline = ConversionPipeline()
    result = pipeline.run(pdf_path, docx_path, context=context)

    assert result.output_path == docx_path.resolve()
    assert context.resources.get("pdf_startxref", 0) > 0
    assert context.resources.get("pdf_cross_reference_kind") in {"table", "stream"}
    trailer_info = context.resources.get("pdf_trailer_info")
    assert trailer_info
    assert trailer_info.get("root_ref") is not None
    assert context.resources.get("pdf_trailer")
    assert context.resources.get("pdf_trailer_dereferenced")
    if trailer_info.get("size") is not None:
        assert context.resources.get("pdf_object_count") == trailer_info.get("size")
    catalog = context.resources.get("pdf_catalog")
    assert catalog
    assert catalog.get("/Type") == "/Catalog"
    pages_tree = context.resources.get("pdf_pages_tree")
    assert pages_tree
    assert pages_tree.get("/Type") == "/Pages"
    pages_summary = context.resources.get("pdf_pages_tree_summary")
    assert pages_summary
    assert pages_summary["type"] == "/Pages"
    assert pages_summary.get("count") == 1
    assert pages_summary.get("kids")
    assert context.resources.get("pdf_pages_ref")
    assert context.resources.get("pdf_pages_count") == 1
    leaf_entries = context.resources.get("pdf_pages_leaves")
    assert leaf_entries
    assert context.resources.get("pdf_pages_leaf_count") == len(leaf_entries)
    page_refs = context.resources.get("pdf_page_refs")
    assert page_refs
    assert page_refs[0] == leaf_entries[0].get("ref")


def test_conversion_pipeline_prepares_page_buffers(tmp_path: Path) -> None:
    pdf_path = tmp_path / "buffers.pdf"
    _create_pdf(pdf_path, "Buffer stage")

    docx_path = tmp_path / "buffers.docx"
    context = ConversionContext()
    pipeline = ConversionPipeline()
    pipeline.run(pdf_path, docx_path, context=context)

    iteration_plan = context.resources.get("page_iteration_plan")
    assert iteration_plan == [0]

    dictionaries = context.resources.get("page_dictionaries")
    assert isinstance(dictionaries, list)
    assert len(dictionaries) == 1
    page_dict = dictionaries[0]
    assert hasattr(page_dict, "get")
    assert str(page_dict.get("/Type")) == "/Page"

    iteration_details = context.resources.get("page_iteration_details")
    assert isinstance(iteration_details, list)
    assert len(iteration_details) == 1
    iteration_entry = iteration_details[0]
    assert iteration_entry.get("page_number") == 0
    assert iteration_entry.get("ordinal") == 0
    assert iteration_entry.get("width") > 0
    assert iteration_entry.get("height") > 0
    assert iteration_entry.get("dictionary_type") == "/Page"

    dictionary_refs = context.resources.get("page_dictionary_refs")
    assert isinstance(dictionary_refs, list)
    assert len(dictionary_refs) == 1
    assert dictionary_refs[0] == iteration_entry.get("object_ref")

    plan = context.resources.get("page_content_plan")
    assert plan == [0]

    buffers = context.resources.get("page_content_buffers")
    assert isinstance(buffers, list)
    assert len(buffers) == 1
    buffer_entry = buffers[0]
    assert buffer_entry.get("page_number") == 0
    assert buffer_entry.get("ordinal") == 0
    assert isinstance(buffer_entry.get("glyphs"), list)
    assert isinstance(buffer_entry.get("images"), list)
    assert isinstance(buffer_entry.get("lines"), list)
    assert isinstance(buffer_entry.get("paths"), list)
    dimensions = buffer_entry.get("dimensions")
    assert dimensions and dimensions["width"] > 0 and dimensions["height"] > 0
    assert buffer_entry.get("glyph_count") == len(buffer_entry.get("glyphs", ()))
    assert buffer_entry.get("image_count") == len(buffer_entry.get("images", ()))

    summary = context.resources.get("page_content_summary")
    assert isinstance(summary, list) and len(summary) == 1
    summary_entry = summary[0]
    assert summary_entry.get("page_number") == 0
    assert summary_entry.get("glyphs") == buffer_entry.get("glyph_count")
    assert summary_entry.get("images") == buffer_entry.get("image_count")


def test_pdf_document_primitives_conversion(tmp_path: Path) -> None:
    page = Page(
        number=0,
        width=200,
        height=200,
        text_blocks=[
            TextBlock(
                text="Hello primitive world",
                bbox=BoundingBox(0, 0, 200, 20),
                font_name="Helvetica",
                font_size=12,
                role="P",
            )
        ],
        images=[],
        lines=[],
        tagged_roles=["P"],
    )
    document = PdfDocument(pages=[page], tagged=True)

    output = tmp_path / "primitive.docx"
    result = convert_document(document, output)

    assert result.output_path == output.resolve()
    assert result.page_count == 1
    assert result.paragraph_count == 1
    assert result.word_count >= 3
    assert result.tagged_pdf is True
    _assert_pipeline_log(result)

    with ZipFile(output) as archive:
        assert "word/document.xml" in archive.namelist()


def test_external_hyperlink_relationships(tmp_path: Path) -> None:
    link_bbox = BoundingBox(10, 60, 150, 80)
    page = Page(
        number=0,
        width=200,
        height=200,
        text_blocks=[
            TextBlock(
                text="Visit Example",
                bbox=link_bbox,
                font_name="Helvetica",
                font_size=12,
                role="P",
            )
        ],
        images=[],
        lines=[],
        links=[Link(bbox=link_bbox, uri="https://example.com", kind="external")],
        tagged_roles=[],
    )
    document = PdfDocument(pages=[page], tagged=False)

    output = tmp_path / "external.docx"
    convert_document(document, output)

    with ZipFile(output) as archive:
        rel_root = ElementTree.parse(archive.open("word/_rels/document.xml.rels")).getroot()
        rel_tag = "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"
        hyperlink_rels = [
            node
            for node in rel_root.findall(rel_tag)
            if node.attrib.get("Target") == "https://example.com"
        ]
        assert hyperlink_rels, "Expected hyperlink relationship to be emitted"
        rid = hyperlink_rels[0].attrib["Id"]
        assert hyperlink_rels[0].attrib.get("TargetMode") == "External"

        doc_root = ElementTree.parse(archive.open("word/document.xml")).getroot()

    ns = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }
    hyperlink = doc_root.find(f".//w:hyperlink[@r:id='{rid}']", ns)
    assert hyperlink is not None
    run_style = hyperlink.find("w:r/w:rPr/w:rStyle", ns)
    assert run_style is not None
    assert run_style.attrib.get(f"{{{ns['w']}}}val") == "Hyperlink"


def test_internal_hyperlink_to_bookmark(tmp_path: Path) -> None:
    target_block = TextBlock(
        text="Target section",
        bbox=BoundingBox(20, 150, 190, 180),
        font_name="Helvetica",
        font_size=14,
        role="H1",
    )
    link_block = TextBlock(
        text="Jump to target",
        bbox=BoundingBox(20, 90, 190, 120),
        font_name="Helvetica",
        font_size=12,
        role="P",
    )
    link = Link(
        bbox=link_block.bbox,
        anchor="target_anchor",
        kind="internal",
        destination_page=0,
        destination_top=target_block.bbox.top,
    )
    page = Page(
        number=0,
        width=200,
        height=200,
        text_blocks=[target_block, link_block],
        images=[],
        lines=[],
        links=[link],
        tagged_roles=[],
    )
    document = PdfDocument(pages=[page], tagged=False)

    output = tmp_path / "internal.docx"
    convert_document(document, output)

    with ZipFile(output) as archive:
        doc_root = ElementTree.parse(archive.open("word/document.xml")).getroot()

    ns = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }
    bookmark = doc_root.find(".//w:bookmarkStart[@w:name='target_anchor']", ns)
    assert bookmark is not None
    hyperlink = None
    for paragraph in doc_root.findall(".//w:p", ns):
        text_parts = [node.text or "" for node in paragraph.findall(".//w:t", ns)]
        if "".join(text_parts).strip() == "Jump to target":
            hyperlink = paragraph.find("w:hyperlink", ns)
            break
    assert hyperlink is not None
    assert hyperlink.attrib.get(f"{{{ns['w']}}}anchor") == "target_anchor"
    assert f"{{{ns['r']}}}id" not in hyperlink.attrib


def test_outline_generates_toc_and_bookmarks(tmp_path: Path) -> None:
    chapter = TextBlock(
        text="Chapter 1",
        bbox=BoundingBox(36, 680, 400, 720),
        font_name="Helvetica-Bold",
        font_size=18,
        role="H1",
    )
    section = TextBlock(
        text="Section 1.1",
        bbox=BoundingBox(48, 640, 400, 670),
        font_name="Helvetica",
        font_size=14,
        role="H2",
    )
    page = Page(
        number=0,
        width=612,
        height=792,
        text_blocks=[chapter, section],
        images=[],
        lines=[],
    )
    outline = [
        OutlineNode(
            title="Chapter 1",
            page_number=0,
            top=chapter.bbox.top,
            anchor="chapter1",
            children=[
                OutlineNode(
                    title="Section 1.1",
                    page_number=0,
                    top=section.bbox.top,
                    anchor="section11",
                )
            ],
        )
    ]
    document = PdfDocument(pages=[page], outline=outline)

    options = ConversionOptions(include_outline_toc=True, generate_toc_field=True)
    output = tmp_path / "outline.docx"
    convert_document(document, output, options=options)

    with ZipFile(output) as archive:
        doc_root = ElementTree.parse(archive.open("word/document.xml")).getroot()

    ns = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }
    bookmark = doc_root.find(".//w:bookmarkStart[@w:name='chapter1']", ns)
    assert bookmark is not None
    toc_paragraphs = [
        paragraph
        for paragraph in doc_root.findall(".//w:p", ns)
        if paragraph.find("w:pPr/w:pStyle[@w:val='TOCHeading']", ns) is not None
    ]
    assert toc_paragraphs, "Expected a TOC heading paragraph"
    assert any(
        "".join(node.text or "" for node in paragraph.findall(".//w:t", ns)).strip()
        == "Table of Contents"
        for paragraph in toc_paragraphs
    ), "Expected TOC heading text"
    toc_instruction = " ".join(
        [
            "TOC",
            "\\" + 'o "1-3"',
            "\\" + "h",
            "\\" + "z",
            "\\" + "u",
        ]
    )
    toc_fields = [
        node
        for node in doc_root.findall(".//w:fldSimple", ns)
        if toc_instruction in node.attrib.get(f"{{{ns['w']}}}instr", "")
    ]
    assert toc_fields, "Expected TOC field instruction to be emitted"
    toc_level_one = [
        paragraph
        for paragraph in doc_root.findall(".//w:p", ns)
        if paragraph.find("w:pPr/w:pStyle[@w:val='TOC1']", ns) is not None
    ]
    assert any(
        (link := paragraph.find("w:hyperlink", ns)) is not None
        and link.attrib.get(f"{{{ns['w']}}}anchor") == "chapter1"
        for paragraph in toc_level_one
    )
    toc_level_two = [
        paragraph
        for paragraph in doc_root.findall(".//w:p", ns)
        if paragraph.find("w:pPr/w:pStyle[@w:val='TOC2']", ns) is not None
    ]
    assert any(
        (link := paragraph.find("w:hyperlink", ns)) is not None
        and link.attrib.get(f"{{{ns['w']}}}anchor") == "section11"
        for paragraph in toc_level_two
    )


def test_outline_toc_field_can_be_disabled(tmp_path: Path) -> None:
    heading = TextBlock(
        text="Intro",
        bbox=BoundingBox(36, 680, 400, 720),
        font_name="Helvetica-Bold",
        font_size=18,
        role="H1",
    )
    page = Page(
        number=0,
        width=612,
        height=792,
        text_blocks=[heading],
        images=[],
        lines=[],
    )
    outline = [
        OutlineNode(
            title="Intro",
            page_number=0,
            top=heading.bbox.top,
            anchor="intro",
        )
    ]
    document = PdfDocument(pages=[page], outline=outline)

    options = ConversionOptions(include_outline_toc=True, generate_toc_field=False)
    output = tmp_path / "outline_no_field.docx"
    convert_document(document, output, options=options)

    with ZipFile(output) as archive:
        doc_root = ElementTree.parse(archive.open("word/document.xml")).getroot()

    ns = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }
    toc_fields = [
        node
        for node in doc_root.findall(".//w:fldSimple", ns)
        if "TOC" in node.attrib.get(f"{{{ns['w']}}}instr", "")
    ]
    assert not toc_fields
    toc_level_one = [
        paragraph
        for paragraph in doc_root.findall(".//w:p", ns)
        if paragraph.find("w:pPr/w:pStyle[@w:val='TOC1']", ns) is not None
    ]
    assert any(
        (link := paragraph.find("w:hyperlink", ns)) is not None
        and link.attrib.get(f"{{{ns['w']}}}anchor") == "intro"
        for paragraph in toc_level_one
    )


def test_cross_page_paragraph_continuity(tmp_path: Path) -> None:
    first = Page(
        number=0,
        width=200,
        height=200,
        text_blocks=[
            TextBlock(
                text="This paragraph continues",
                bbox=BoundingBox(0, 0, 200, 20),
                font_name="Helvetica",
                font_size=12,
            )
        ],
        images=[],
        lines=[],
    )
    second = Page(
        number=1,
        width=200,
        height=200,
        text_blocks=[
            TextBlock(
                text="on the next page.",
                bbox=BoundingBox(0, 0, 200, 20),
                font_name="Helvetica",
                font_size=12,
            )
        ],
        images=[],
        lines=[],
    )
    document = PdfDocument(pages=[first, second])
    output = tmp_path / "continuity.docx"
    convert_document(document, output)

    with ZipFile(output) as archive:
        document_xml = archive.read("word/document.xml")
    assert b"This paragraph continues" in document_xml
    assert b"next page" in document_xml
    assert b"This paragraph continues" in document_xml
    assert document_xml.count(b"This paragraph continues") == 1


def test_table_detection_from_lines(tmp_path: Path) -> None:
    text_blocks = [
        TextBlock(text="A1", bbox=BoundingBox(10, 60, 40, 80)),
        TextBlock(text="A2", bbox=BoundingBox(60, 60, 90, 80)),
        TextBlock(text="B1", bbox=BoundingBox(10, 20, 40, 40)),
        TextBlock(text="B2", bbox=BoundingBox(60, 20, 90, 40)),
    ]
    lines = [
        Line(start=(10, 40), end=(90, 40)),
        Line(start=(10, 80), end=(90, 80)),
        Line(start=(10, 20), end=(10, 80)),
        Line(start=(90, 20), end=(90, 80)),
    ]
    page = Page(number=0, width=120, height=120, text_blocks=text_blocks, images=[], lines=lines)
    document = PdfDocument(pages=[page])

    output = tmp_path / "table.docx"
    convert_document(document, output)

    with ZipFile(output) as archive:
        document_xml = archive.read("word/document.xml")
    assert b"<w:tbl" in document_xml


def test_table_detection_from_tagged_roles(tmp_path: Path) -> None:
    text_blocks = [
        TextBlock(
            text="Header 1",
            bbox=BoundingBox(10, 120, 50, 150),
            role="TH",
            font_name="Helvetica",
            font_size=12,
            bold=True,
        ),
        TextBlock(
            text="Header 2",
            bbox=BoundingBox(50, 120, 90, 150),
            role="TH",
            font_name="Helvetica",
            font_size=12,
            bold=True,
        ),
        TextBlock(
            text="Row 1",
            bbox=BoundingBox(10, 80, 50, 110),
            role="TD",
            font_name="Helvetica",
            font_size=11,
        ),
        TextBlock(
            text="Row 2",
            bbox=BoundingBox(50, 80, 90, 110),
            role="TD",
            font_name="Helvetica",
            font_size=11,
        ),
    ]
    page = Page(
        number=0,
        width=120,
        height=160,
        text_blocks=text_blocks,
        images=[],
        lines=[],
        tagged_roles=["Table", "TR", "TD"],
    )
    document = PdfDocument(pages=[page], tagged=True)

    output = tmp_path / "tagged-table.docx"
    convert_document(document, output)

    with ZipFile(output) as archive:
        xml = ElementTree.fromstring(archive.read("word/document.xml"))

    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    header_nodes = xml.findall(
        ".//w:tbl/w:tr/w:trPr/w:tblHeader",
        ns,
    )
    shading_nodes = xml.findall(
        ".//w:tbl/w:tr[1]/w:tc/w:tcPr/w:shd",
        ns,
    )
    assert header_nodes
    assert any(node.get(f"{{{ns['w']}}}fill") == "D9D9D9" for node in shading_nodes)


def test_image_deduplication(tmp_path: Path) -> None:
    png = _png_bytes(8, 8)
    images = [
        Image(data=png, bbox=BoundingBox(0, 0, 40, 40), mime_type="image/png", name="img1"),
        Image(data=png, bbox=BoundingBox(50, 0, 90, 40), mime_type="image/png", name="img2"),
    ]
    page = Page(number=0, width=200, height=200, text_blocks=[], images=images, lines=[])
    document = PdfDocument(pages=[page])

    output = tmp_path / "images.docx"
    convert_document(document, output)

    with ZipFile(output) as archive:
        media = [name for name in archive.namelist() if name.startswith("word/media/")]
    assert len(media) == 1


def test_table_detection_from_whitespace_grid(tmp_path: Path) -> None:
    text_blocks = [
        TextBlock(text="Q1", bbox=BoundingBox(10, 140, 40, 160), font_name="Helvetica", font_size=11),
        TextBlock(text="Q2", bbox=BoundingBox(60, 140, 90, 160), font_name="Helvetica", font_size=11),
        TextBlock(text="10", bbox=BoundingBox(10, 100, 40, 120), font_name="Helvetica", font_size=11),
        TextBlock(text="20", bbox=BoundingBox(60, 100, 90, 120), font_name="Helvetica", font_size=11),
    ]
    page = Page(
        number=0,
        width=140,
        height=180,
        text_blocks=text_blocks,
        images=[],
        lines=[],
    )
    document = PdfDocument(pages=[page])

    output = tmp_path / "grid-table.docx"
    convert_document(document, output)

    with ZipFile(output) as archive:
        xml = ElementTree.fromstring(archive.read("word/document.xml"))

    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    grid_cols = xml.findall(".//w:tbl/w:tblGrid/w:gridCol", ns)
    assert len(grid_cols) == 2
    right_aligned = xml.findall(
        ".//w:tbl/w:tr[2]/w:tc[2]/w:p/w:pPr/w:jc[@w:val='right']",
        ns,
    )
    assert right_aligned


def test_table_detection_colspan_and_rowspan(tmp_path: Path) -> None:
    text_blocks = [
        TextBlock(
            text="Merged Header",
            bbox=BoundingBox(10, 180, 90, 200),
            role="TH",
            font_name="Helvetica",
            font_size=12,
            bold=True,
        ),
        TextBlock(
            text="Left",
            bbox=BoundingBox(10, 100, 50, 180),
            role="TD",
            font_name="Helvetica",
            font_size=11,
        ),
        TextBlock(
            text="Top Right",
            bbox=BoundingBox(50, 140, 90, 180),
            role="TD",
            font_name="Helvetica",
            font_size=11,
        ),
        TextBlock(
            text="Bottom Right",
            bbox=BoundingBox(50, 100, 90, 140),
            role="TD",
            font_name="Helvetica",
            font_size=11,
        ),
    ]
    page = Page(
        number=0,
        width=160,
        height=220,
        text_blocks=text_blocks,
        images=[],
        lines=[],
        tagged_roles=["Table", "TR", "TD"],
    )
    document = PdfDocument(pages=[page], tagged=True)

    output = tmp_path / "span-table.docx"
    convert_document(document, output)

    with ZipFile(output) as archive:
        xml_bytes = archive.read("word/document.xml")
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    root = ElementTree.fromstring(xml_bytes)

    grid_spans = root.findall(".//w:tbl//w:gridSpan", ns)
    assert any(span.get(f"{{{ns['w']}}}val") == "2" for span in grid_spans)

    vmerges = root.findall(".//w:tbl//w:vMerge", ns)
    values = [merge.get(f"{{{ns['w']}}}val") for merge in vmerges]
    assert "restart" in values
    assert any(val is None for val in values)


def test_image_relationship_written(tmp_path: Path) -> None:
    png_header = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0bIDATx\x9cc``\x00\x00\x00\x02\x00\x01"
        b"\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    image = Image(
        data=png_header,
        bbox=BoundingBox(0, 0, 10, 10),
        mime_type="image/png",
        name="TestImage",
    )
    page = Page(
        number=0,
        width=100,
        height=100,
        text_blocks=[],
        images=[image],
        lines=[],
    )
    document = PdfDocument(pages=[page])

    output = tmp_path / "image.docx"
    convert_document(document, output)

    with ZipFile(output) as archive:
        rels = archive.read("word/_rels/document.xml.rels")
        media_files = [name for name in archive.namelist() if name.startswith("word/media/")]
    assert b"http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" in rels
    assert media_files


def test_pdf_reader_flate_image_extraction(tmp_path: Path) -> None:
    import zlib

    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)

    raw = bytes([255, 0, 0] * 4)
    encoded = zlib.compress(raw)
    image_stream = StreamObject()
    image_stream.update(
        {
            NameObject("/Type"): NameObject("/XObject"),
            NameObject("/Subtype"): NameObject("/Image"),
            NameObject("/Width"): NumberObject(2),
            NameObject("/Height"): NumberObject(2),
            NameObject("/ColorSpace"): NameObject("/DeviceRGB"),
            NameObject("/BitsPerComponent"): NumberObject(8),
            NameObject("/Filter"): NameObject("/FlateDecode"),
        }
    )
    image_stream._data = encoded
    image_ref = writer._add_object(image_stream)

    resources = DictionaryObject({NameObject("/XObject"): DictionaryObject({NameObject("/Im1"): image_ref})})
    page[NameObject("/Resources")] = resources

    content = StreamObject()
    content._data = b"q 200 0 0 200 50 60 cm /Im1 Do Q"
    content[NameObject("/Length")] = NumberObject(len(content._data))
    page[NameObject("/Contents")] = writer._add_object(content)

    pdf_path = tmp_path / "with-image.pdf"
    with pdf_path.open("wb") as fh:
        writer.write(fh)

    docx_path = tmp_path / "with-image.docx"
    convert_document(pdf_path, docx_path)

    with ZipFile(docx_path) as archive:
        media = [name for name in archive.namelist() if name.startswith("word/media/")]
        assert any(name.endswith(".png") for name in media)
        xml = archive.read("word/document.xml")

    root = ElementTree.fromstring(xml)
    ns = {"wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"}
    extent = root.find(".//wp:extent", ns)
    assert extent is not None
    cx = int(extent.attrib["cx"])
    cy = int(extent.attrib["cy"])
    assert cx == pytest.approx(int(round(200 * 12700)))
    assert cy == pytest.approx(int(round(200 * 12700)))


def test_jpx_image_placeholder(tmp_path: Path) -> None:
    writer = PdfWriter()
    page = writer.add_blank_page(width=100, height=100)
    image_stream = StreamObject()
    image_stream.update(
        {
            NameObject("/Type"): NameObject("/XObject"),
            NameObject("/Subtype"): NameObject("/Image"),
            NameObject("/Width"): NumberObject(1),
            NameObject("/Height"): NumberObject(1),
            NameObject("/ColorSpace"): NameObject("/DeviceRGB"),
            NameObject("/BitsPerComponent"): NumberObject(8),
            NameObject("/Filter"): NameObject("/JPXDecode"),
        }
    )
    image_stream._data = b"JPXDATA"
    image_ref = writer._add_object(image_stream)
    resources = DictionaryObject({NameObject("/XObject"): DictionaryObject({NameObject("/Im1"): image_ref})})
    page[NameObject("/Resources")] = resources

    content = StreamObject()
    content._data = b"q 50 0 0 50 0 0 cm /Im1 Do Q"
    content[NameObject("/Length")] = NumberObject(len(content._data))
    page[NameObject("/Contents")] = writer._add_object(content)

    pdf_path = tmp_path / "jpx.pdf"
    with pdf_path.open("wb") as fh:
        writer.write(fh)

    docx_path = tmp_path / "jpx.docx"
    convert_document(pdf_path, docx_path)

    with ZipFile(docx_path) as archive:
        media = [name for name in archive.namelist() if name.startswith("word/media/")]
        assert len(media) == 1
        data = archive.read(media[0])
    assert data.startswith(b"\x89PNG\r\n\x1a\n")


def test_pdf_reader_smask_alpha(tmp_path: Path) -> None:
    import zlib

    writer = PdfWriter()
    page = writer.add_blank_page(width=120, height=120)

    image_stream = StreamObject()
    image_stream.update(
        {
            NameObject("/Type"): NameObject("/XObject"),
            NameObject("/Subtype"): NameObject("/Image"),
            NameObject("/Width"): NumberObject(1),
            NameObject("/Height"): NumberObject(1),
            NameObject("/ColorSpace"): NameObject("/DeviceRGB"),
            NameObject("/BitsPerComponent"): NumberObject(8),
            NameObject("/Filter"): NameObject("/FlateDecode"),
        }
    )
    image_stream._data = zlib.compress(bytes([255, 0, 0]))

    smask_stream = StreamObject()
    smask_stream.update(
        {
            NameObject("/Type"): NameObject("/XObject"),
            NameObject("/Subtype"): NameObject("/Image"),
            NameObject("/Width"): NumberObject(1),
            NameObject("/Height"): NumberObject(1),
            NameObject("/ColorSpace"): NameObject("/DeviceGray"),
            NameObject("/BitsPerComponent"): NumberObject(8),
        }
    )
    smask_stream._data = bytes([128])
    smask_ref = writer._add_object(smask_stream)
    image_stream[NameObject("/SMask")] = smask_ref
    image_ref = writer._add_object(image_stream)

    resources = DictionaryObject({NameObject("/XObject"): DictionaryObject({NameObject("/Im1"): image_ref})})
    page[NameObject("/Resources")] = resources

    content = StreamObject()
    content._data = b"q 60 0 0 60 10 10 cm /Im1 Do Q"
    content[NameObject("/Length")] = NumberObject(len(content._data))
    page[NameObject("/Contents")] = writer._add_object(content)

    pdf_path = tmp_path / "smask.pdf"
    with pdf_path.open("wb") as fh:
        writer.write(fh)

    docx_path = tmp_path / "smask.docx"
    convert_document(pdf_path, docx_path)

    with ZipFile(docx_path) as archive:
        media = [name for name in archive.namelist() if name.startswith("word/media/")]
        assert media
        data = archive.read(media[0])
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    color_type = data[25]
    assert color_type == 6  # RGBA


def test_line_rasterisation(tmp_path: Path) -> None:
    lines = [Line(start=(10, 10), end=(90, 90))]
    page = Page(number=0, width=100, height=100, text_blocks=[], images=[], lines=lines)
    document = PdfDocument(pages=[page])

    docx_path = tmp_path / "line.docx"
    convert_document(document, docx_path)

    with ZipFile(docx_path) as archive:
        media = [name for name in archive.namelist() if name.startswith("word/media/")]
        assert media
        for name in media:
            assert archive.read(name).startswith(b"\x89PNG\r\n\x1a\n")


def test_annotation_and_list_rendering(tmp_path: Path) -> None:
    text_blocks = [
        TextBlock(
            text="- First bullet",
            bbox=BoundingBox(10, 120, 190, 140),
            font_name="Helvetica",
            font_size=11,
            role="LI",
        ),
        TextBlock(
            text="Important note",
            bbox=BoundingBox(10, 80, 190, 100),
            role="Annotation",
        ),
        TextBlock(
            text="Heading",
            bbox=BoundingBox(10, 40, 190, 60),
            role="H1",
        ),
    ]
    line = Line(start=(0, 10), end=(200, 10))
    page = Page(
        number=0,
        width=200,
        height=200,
        text_blocks=text_blocks,
        images=[],
        lines=[line],
    )
    document = PdfDocument(pages=[page])

    output = tmp_path / "annotation.docx"
    convert_document(document, output)

    with ZipFile(output) as archive:
        document_xml = archive.read("word/document.xml")
        media = [name for name in archive.namelist() if name.startswith("word/media/")]

    assert b"First bullet" in document_xml
    assert b"w:numPr" in document_xml
    assert b"Important note" in document_xml
    assert b"Heading" in document_xml
    assert media
    assert any(name.endswith(".png") for name in media)
    assert b"<w:drawing" in document_xml


def test_header_footer_detection_with_first_page(tmp_path: Path) -> None:
    width, height = 612.0, 792.0
    pages: list[Page] = []
    header_texts = ["Report Title", "Quarterly Report", "Quarterly Report"]
    for index, header_text in enumerate(header_texts):
        text_blocks = [
            TextBlock(
                text=header_text,
                bbox=BoundingBox(72.0, height - 42.0, width - 72.0, height - 18.0),
                font_name="Helvetica",
                font_size=14,
                bold=True,
            ),
            TextBlock(
                text=f"Body paragraph {index + 1}",
                bbox=BoundingBox(72.0, 360.0, width - 72.0, 380.0),
                font_name="Helvetica",
                font_size=12,
            ),
            TextBlock(
                text=f"Page {index + 1}",
                bbox=BoundingBox(width / 2 - 20.0, 20.0, width / 2 + 40.0, 40.0),
                font_name="Helvetica",
                font_size=10,
            ),
        ]
        pages.append(Page(number=index, width=width, height=height, text_blocks=text_blocks, images=[], lines=[]))

    document = PdfDocument(pages=pages)

    output = tmp_path / "headers.docx"
    convert_document(document, output)

    with ZipFile(output) as archive:
        names = set(archive.namelist())
        assert "word/header1.xml" in names
        assert "word/header1_first.xml" in names
        assert "word/footer1.xml" in names
        document_xml = ElementTree.fromstring(archive.read("word/document.xml"))
        relationships_xml = ElementTree.fromstring(archive.read("word/_rels/document.xml.rels"))
        default_header = archive.read("word/header1.xml")
        first_header = archive.read("word/header1_first.xml")
        default_footer = ElementTree.fromstring(archive.read("word/footer1.xml"))

    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    rel_ns = {"rel": "http://schemas.openxmlformats.org/package/2006/relationships"}

    assert document_xml.find(".//w:sectPr/w:titlePg", ns) is not None
    header_refs = document_xml.findall(".//w:sectPr/w:headerReference", ns)
    ref_types = {ref.get(f"{{{ns['w']}}}type") for ref in header_refs}
    assert {"default", "first"}.issubset(ref_types)

    rel_targets = {
        rel.get("Target")
        for rel in relationships_xml.findall("rel:Relationship", rel_ns)
        if rel.get("Type")
        == "http://schemas.openxmlformats.org/officeDocument/2006/relationships/header"
        or rel.get("Type")
        == "http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer"
    }
    assert "header1.xml" in rel_targets
    assert "header1_first.xml" in rel_targets
    assert "footer1.xml" in rel_targets

    assert b"Quarterly Report" in default_header
    assert b"Report Title" in first_header
    body_xml = ElementTree.tostring(document_xml, encoding="utf-8")
    assert b"Quarterly Report" not in body_xml
    assert b"Report Title" not in body_xml

    fields = {
        instr.strip()
        for fld in default_footer.findall(".//w:fldSimple", ns)
        if (instr := fld.get(f"{{{ns['w']}}}instr"))
    }
    assert "PAGE" in fields
    assert "NUMPAGES" in fields


def test_conversion_metadata_override(tmp_path: Path) -> None:
    pdf_path = tmp_path / "meta.pdf"
    _create_pdf(pdf_path, "Meta Test")

    metadata = ConversionMetadata(
        title="Custom Title",
        author="Author",
        subject="Subject",
        description="Description",
        keywords=["one", "two"],
        created=datetime(2024, 1, 1, tzinfo=timezone.utc),
        modified=datetime(2024, 1, 2, tzinfo=timezone.utc),
        language="fr-FR",
        revision="5",
        last_modified_by="Metadata Bot",
    )

    docx_path = tmp_path / "meta.docx"
    convert_document(pdf_path, docx_path, metadata=metadata)

    with ZipFile(docx_path) as archive:
        core_xml = archive.read("docProps/core.xml")
    assert b"Custom Title" in core_xml
    assert b"Author" in core_xml
    assert b"Subject" in core_xml
    assert b"one, two" in core_xml
    assert b"fr-FR" in core_xml
    assert b">5<" in core_xml
    assert b"Metadata Bot" in core_xml


def test_pdf_metadata_transfer(tmp_path: Path) -> None:
    pdf_path = tmp_path / "meta_source.pdf"
    metadata_map = {
        "/Title": "Source Title",
        "/Author": "Source Author",
        "/Subject": "Source Subject",
        "/Keywords": "alpha, beta",
        "/CreationDate": "D:20240304050607Z",
        "/ModDate": "D:20240506070809Z",
        "/Lang": "en-US",
        "/Revision": "7",
        "/LastModifiedBy": "Revision Agent",
    }
    _create_pdf(pdf_path, "Metadata sample content", metadata=metadata_map)

    docx_path = tmp_path / "meta_source.docx"
    convert_document(pdf_path, docx_path)

    with ZipFile(docx_path) as archive:
        core_xml = archive.read("docProps/core.xml")
        app_xml = archive.read("docProps/app.xml")

    assert b"Source Title" in core_xml
    assert b"Source Author" in core_xml
    assert b"Source Subject" in core_xml
    assert b"alpha, beta" in core_xml
    assert b"en-US" in core_xml
    assert b">7<" in core_xml
    assert b"Revision Agent" in core_xml
    assert b"2024-03-04T05:06:07Z" in core_xml
    assert b"2024-05-06T07:08:09Z" in core_xml

    assert b"<ep:Pages>1</ep:Pages>" in app_xml
    assert b"<ep:Paragraphs>1</ep:Paragraphs>" in app_xml
    assert b"<ep:Words>3</ep:Words>" in app_xml
    assert b"<ep:Lines>1</ep:Lines>" in app_xml
    assert b"<ep:Characters>23</ep:Characters>" in app_xml
    assert b"<ep:CharactersWithSpaces>23</ep:CharactersWithSpaces>" in app_xml


def test_document_builder_internal_paths() -> None:
    metadata = DocumentMetadata()
    builder = _DocumentBuilder(metadata, strip_whitespace=True)
    page = Page(number=0, width=100, height=100, text_blocks=[], images=[], lines=[])
    section = builder.ensure_section(page, 0)

    blank_block = TextBlock(text="   ", bbox=BoundingBox(0, 0, 10, 10))
    builder.add_text_block(section, blank_block, 0)
    assert builder._pending_paragraph is None

    first_block = TextBlock(
        text="Sentence ends.",
        bbox=BoundingBox(0, 60, 50, 80),
        font_name="Helvetica",
        font_size=12,
        role="P",
    )
    builder.add_text_block(section, first_block, 0)

    builder._pending_paragraph = None
    standalone_block = TextBlock(text="Standalone", bbox=BoundingBox(0, 30, 50, 40), font_size=12)
    builder._append_run("Standalone", standalone_block)
    assert builder._pending_paragraph is not None

    builder._pending_paragraph = IRParagraph(runs=[IRRun(text="Prev")], role="P")
    builder._previous_block = first_block
    builder._previous_page_number = 0
    far_block = TextBlock(
        text="Next block",
        bbox=BoundingBox(0, 0, 50, 10),
        font_size=12,
        role="P",
    )
    assert builder._can_continue(far_block, 0) is False

    heading_block = TextBlock(
        text="Heading",
        bbox=BoundingBox(0, 40, 50, 60),
        font_size=12,
        role="H1",
    )
    assert builder._can_continue(heading_block, 0) is False

    builder._pending_paragraph = IRParagraph(runs=[IRRun(text="Prev")], role="P")
    builder._previous_block = first_block
    builder._previous_page_number = 0
    builder._pending_continue = False
    assert builder._can_continue(first_block, 1) is False

    builder.add_element(section, IRParagraph(runs=[IRRun(text="Added")]))
    builder.end_page(section)
    result = builder.build(tagged=False, page_count=1)
    assert result.sections


def test_document_builder_section_margins_and_columns() -> None:
    metadata = DocumentMetadata()
    builder = _DocumentBuilder(metadata, strip_whitespace=True)
    page = Page(
        number=0,
        width=612.0,
        height=792.0,
        text_blocks=[
            TextBlock(text="Column 1 A", bbox=BoundingBox(72, 700, 220, 720), font_size=12),
            TextBlock(text="Column 1 B", bbox=BoundingBox(72, 660, 230, 680), font_size=12),
            TextBlock(text="Column 2 A", bbox=BoundingBox(330, 700, 520, 720), font_size=12),
            TextBlock(text="Column 2 B", bbox=BoundingBox(330, 660, 530, 680), font_size=12),
            TextBlock(text="Footer.", bbox=BoundingBox(72, 72, 200, 92), font_size=12),
        ],
        images=[],
        lines=[],
    )
    builder.process_page(page, 0)
    document = builder.build(tagged=False, page_count=1)

    assert len(document.sections) == 1
    section = document.sections[0]
    assert section.margin_left == pytest.approx(72.0, rel=0.05)
    assert section.margin_right == pytest.approx(82.0, rel=0.15)
    assert section.margin_top == pytest.approx(72.0, rel=0.1)
    assert section.margin_bottom == pytest.approx(72.0, rel=0.2)
    assert section.columns == 2
    assert section.column_spacing is not None and section.column_spacing > 0
    assert section.orientation == "portrait"


def test_document_builder_page_and_column_breaks() -> None:
    metadata = DocumentMetadata()
    builder = _DocumentBuilder(metadata, strip_whitespace=True)
    page_one = Page(
        number=0,
        width=612.0,
        height=792.0,
        text_blocks=[
            TextBlock(text="Page 1 Column 1", bbox=BoundingBox(72, 772, 260, 792), font_size=12),
            TextBlock(text="Page 1 Column 1B", bbox=BoundingBox(72, 732, 260, 752), font_size=12),
            TextBlock(text="Page 1 Column 2", bbox=BoundingBox(330, 772, 520, 792), font_size=12),
            TextBlock(text="Page 1 Column 2B", bbox=BoundingBox(330, 732, 520, 752), font_size=12),
            TextBlock(text="Page 1 Footer.", bbox=BoundingBox(72, 72, 200, 92), font_size=12),
        ],
        images=[],
        lines=[],
    )
    page_two = Page(
        number=1,
        width=612.0,
        height=792.0,
        text_blocks=[
            TextBlock(text="Page 2 Column 1", bbox=BoundingBox(72, 772, 260, 792), font_size=12),
            TextBlock(text="Page 2 Column 1B", bbox=BoundingBox(72, 732, 260, 752), font_size=12),
            TextBlock(text="Page 2 Column 2", bbox=BoundingBox(330, 772, 520, 792), font_size=12),
            TextBlock(text="Page 2 Column 2B", bbox=BoundingBox(330, 732, 520, 752), font_size=12),
            TextBlock(text="Page 2 Footer.", bbox=BoundingBox(72, 72, 200, 92), font_size=12),
        ],
        images=[],
        lines=[],
    )

    builder.process_page(page_one, 0)
    builder.process_page(page_two, 1)
    document = builder.build(tagged=False, page_count=2)

    assert len(document.sections) == 1
    section = document.sections[0]
    paragraphs = [element for element in section.elements if isinstance(element, IRParagraph)]
    assert paragraphs

    column_two_paragraph = next(
        paragraph for paragraph in paragraphs if paragraph.text().startswith("Page 1 Column 2")
    )
    assert column_two_paragraph.column_break_before is True

    page_two_paragraphs = [
        paragraph
        for paragraph in paragraphs
        if paragraph.metadata and paragraph.metadata.get("start_page") == "1"
    ]
    assert page_two_paragraphs
    assert page_two_paragraphs[0].page_break_before is True


def test_document_builder_detects_nested_bullet_lists() -> None:
    metadata = DocumentMetadata()
    builder = _DocumentBuilder(metadata, strip_whitespace=True)
    page = Page(number=0, width=600, height=800, text_blocks=[], images=[], lines=[])
    section = builder.ensure_section(page, 0)

    blocks = [
        TextBlock(text="• First", bbox=BoundingBox(90, 700, 300, 720), font_size=12),
        TextBlock(text="• Second", bbox=BoundingBox(90, 660, 300, 680), font_size=12),
        TextBlock(text="– Nested", bbox=BoundingBox(108, 620, 320, 640), font_size=12),
    ]

    for block in blocks:
        builder.add_text_block(section, block, 0)

    builder.flush_pending(section)

    paragraphs = [element for element in section.elements if isinstance(element, IRParagraph)]
    assert len(paragraphs) == 3
    assert all(paragraph.numbering is not None for paragraph in paragraphs)
    assert [paragraph.numbering.level for paragraph in paragraphs] == [0, 0, 1]
    assert all(paragraph.numbering.kind == "bullet" for paragraph in paragraphs)


def test_document_builder_detects_mixed_ordered_lists() -> None:
    metadata = DocumentMetadata()
    builder = _DocumentBuilder(metadata, strip_whitespace=True)
    page = Page(number=0, width=600, height=800, text_blocks=[], images=[], lines=[])
    section = builder.ensure_section(page, 0)

    blocks = [
        TextBlock(text="1. Intro", bbox=BoundingBox(90, 520, 340, 540), font_size=12),
        TextBlock(text="a) Detail", bbox=BoundingBox(108, 480, 360, 500), font_size=12),
        TextBlock(text="(i) Deep", bbox=BoundingBox(126, 440, 380, 460), font_size=12),
    ]

    for block in blocks:
        builder.add_text_block(section, block, 0)

    builder.flush_pending(section)

    paragraphs = [element for element in section.elements if isinstance(element, IRParagraph)]
    assert len(paragraphs) == 3
    assert [paragraph.numbering.level for paragraph in paragraphs] == [0, 1, 2]
    assert [paragraph.numbering.format for paragraph in paragraphs] == [
        "decimal",
        "lowerLetter",
        "lowerRoman",
    ]
    assert [paragraph.numbering.punctuation for paragraph in paragraphs] == [
        "dot",
        "paren",
        "enclosed",
    ]


def test_paragraph_spacing_alignment_and_styles() -> None:
    metadata = DocumentMetadata()
    builder = _DocumentBuilder(metadata, strip_whitespace=True)
    page = Page(number=0, width=600, height=800, text_blocks=[], images=[], lines=[])
    section = builder.ensure_section(page, 0)

    heading_block = TextBlock(
        text="Centered Heading",
        bbox=BoundingBox(180, 700, 420, 720),
        font_name="Helvetica-Bold",
        font_size=24,
        role="H1",
    )
    builder.add_text_block(section, heading_block, 0)

    body_block = TextBlock(
        text="Body paragraph content goes here.",
        bbox=BoundingBox(72, 640, 400, 660),
        font_name="Times-Roman",
        font_size=12,
        role="P",
    )
    builder.add_text_block(section, body_block, 0)

    builder.flush_pending(section)

    assert len(section.elements) == 2
    heading = section.elements[0]
    assert isinstance(heading, IRParagraph)
    assert heading.style == "Heading1"
    assert heading.keep_lines is True and heading.keep_with_next is True
    assert heading.alignment == "center"
    assert heading.spacing_after == pytest.approx(40.0, rel=0.05)

    body = section.elements[1]
    assert isinstance(body, IRParagraph)
    assert body.spacing_before == pytest.approx(40.0, rel=0.05)
    assert body.line_spacing == pytest.approx(1.67, rel=0.05)
    assert body.alignment == "left"
    assert body.spacing_after == pytest.approx(7.2, rel=0.05)
    assert body.keep_with_next is False


def test_converter_helpers() -> None:
    text, numbering = _normalise_text_for_numbering("1. Ordered", None)
    assert text.endswith("Ordered")
    assert numbering is not None
    assert numbering.kind == "ordered"
    assert numbering.format == "decimal"
    assert numbering.punctuation == "dot"

    _, alpha_numbering = _normalise_text_for_numbering("a) Lettered", None)
    assert alpha_numbering is not None
    assert alpha_numbering.kind == "ordered"
    assert alpha_numbering.format == "lowerLetter"
    assert alpha_numbering.punctuation == "paren"

    _, roman_numbering = _normalise_text_for_numbering("(i) Roman", None)
    assert roman_numbering is not None
    assert roman_numbering.kind == "ordered"
    assert roman_numbering.format == "lowerRoman"
    assert roman_numbering.punctuation == "enclosed"

    paragraphs = _blocks_to_paragraphs_static(
        [
            TextBlock(text=" first", bbox=BoundingBox(0, 40, 10, 60)),
            TextBlock(text="second", bbox=BoundingBox(0, 10, 10, 30)),
        ],
        strip_whitespace=False,
    )
    assert paragraphs and paragraphs[0].runs[0].text.startswith(" first")

    assert _parse_pdf_date("D:20240101120000+05'30'") is not None
    assert _parse_pdf_date("Invalid") is None


def test_write_docx_styles(tmp_path: Path) -> None:
    section = IRSection(page_width=200, page_height=200)
    section.elements = [
        IRParagraph(runs=[IRRun(text="Title text")], role="Title"),
        IRParagraph(
            runs=[
                IRRun(
                    text="Styled",
                    bold=True,
                    italic=True,
                    underline=True,
                    font_name="Arial",
                    font_size=14,
                    color="FF0000",
                )
            ],
            alignment="center",
        ),
    ]
    document = IRDocument(
        metadata=DocumentMetadata(),
        sections=[section],
        tagged_pdf=False,
        page_count=1,
    )
    output = tmp_path / "styled.docx"
    stats = write_docx(document, output)
    assert stats.paragraphs == 2


def test_blocks_to_paragraphs_static_preserves_formatting() -> None:
    block = TextBlock(
        text="Ligature ﬁ example",
        bbox=BoundingBox(0, 0, 100, 20),
        font_name="Example-BoldItalic",
        font_size=11,
        color="112233",
        bold=True,
        italic=True,
        underline=True,
        rtl=True,
        language="ar-SA",
        superscript=True,
    )
    paragraphs = _blocks_to_paragraphs_static([block], strip_whitespace=False)
    assert len(paragraphs) == 1
    run = paragraphs[0].runs[0]
    assert run.bold is True
    assert run.italic is True
    assert run.underline is True
    assert run.color == "112233"
    assert run.superscript is True
    assert run.rtl is True
    assert run.language == "ar-SA"
    assert paragraphs[0].bidi is True


def test_apply_translation_map_prefers_longest_sequence() -> None:
    mapping = {"ab": "X", "a": "A", "c": "see"}
    decoded = _apply_translation_map("abc", mapping, max_key_length=2)
    assert decoded == "Xsee"


def test_font_translation_map_decodes_tounicode_stream() -> None:
    to_unicode_stream = StreamObject()
    cmap_data = b"""/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n/CIDSystemInfo\n<< /Registry (Adobe)\n/Ordering (UCS)\n/Supplement 0\n>> def\n/CMapName /Adobe-Identity-UCS def\n/CMapType 2 def\n1 begincodespacerange\n<01> <01>\nendcodespacerange\n1 beginbfchar\n<01> <03A9>\nendbfchar\nendcmap\nCMapName currentdict /CMap defineresource pop\nend\nend\n"""
    to_unicode_stream._data = cmap_data
    to_unicode_stream[NameObject("/Length")] = NumberObject(len(cmap_data))
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type0"),
            NameObject("/BaseFont"): NameObject("/Custom"),
            NameObject("/ToUnicode"): to_unicode_stream,
        }
    )
    resources = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    page = DictionaryObject({NameObject("/Resources"): resources})

    maps = _font_translation_maps(page)
    assert maps
    translation, max_key_length = maps[id(font)]
    decoded = _apply_translation_map("\x01", translation, max_key_length)
    assert decoded == "Ω"


def test_vertical_matrix_detection() -> None:
    assert _is_vertical_matrix([0.0, 12.0, -12.0, 0.0, 100.0, 200.0]) is True
    assert _is_vertical_matrix([12.0, 0.0, 0.0, 12.0, 100.0, 200.0]) is False


def test_text_fragments_infer_east_asian_languages() -> None:
    japanese_blocks = text_fragments_to_blocks(
        [CapturedText(text="漢かな", x=120.0, y=700.0, font_name="Mincho", font_size=12.0)],
        page_width=400.0,
        page_height=800.0,
        roles=[],
        strip_whitespace=False,
    )
    assert japanese_blocks[0].language == "ja-JP"

    korean_blocks = text_fragments_to_blocks(
        [CapturedText(text="한글", x=120.0, y=660.0, font_name="Batang", font_size=12.0)],
        page_width=400.0,
        page_height=800.0,
        roles=[],
        strip_whitespace=False,
    )
    assert korean_blocks[0].language == "ko-KR"

    chinese_blocks = text_fragments_to_blocks(
        [CapturedText(text="汉字", x=120.0, y=620.0, font_name="SimSun", font_size=12.0)],
        page_width=400.0,
        page_height=800.0,
        roles=[],
        strip_whitespace=False,
    )
    assert chinese_blocks[0].language == "zh-CN"


def test_vertical_text_emits_breaks_and_language(tmp_path: Path) -> None:
    fragments = [
        CapturedText(text="あ", x=140.0, y=740.0, font_name="Mincho", font_size=14.0, vertical=True),
        CapturedText(text="い", x=140.0, y=720.0, font_name="Mincho", font_size=14.0, vertical=True),
    ]
    blocks = text_fragments_to_blocks(
        fragments,
        page_width=400.0,
        page_height=800.0,
        roles=["P"],
        strip_whitespace=False,
    )
    assert len(blocks) == 1
    block = blocks[0]
    assert block.vertical is True
    assert block.language == "ja-JP"
    assert block.text == "あい"

    page = Page(
        number=0,
        width=400.0,
        height=800.0,
        text_blocks=blocks,
        images=[],
        lines=[],
    )
    metadata = DocumentMetadata()
    builder = _DocumentBuilder(metadata, strip_whitespace=True)
    builder.process_page(page, 0)
    document = builder.build(tagged=False, page_count=1)

    output = tmp_path / "vertical.docx"
    write_docx(document, output)

    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with ZipFile(output) as archive:
        doc_xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(doc_xml)
    run = root.find(".//w:body/w:p/w:r", ns)
    assert run is not None
    texts = [node.text for node in run.findall("w:t", ns) if node.text]
    assert "".join(texts) == "あい"
    breaks = run.findall("w:br", ns)
    assert len(breaks) == len(block.text) - 1
    lang = run.find("w:rPr/w:lang", ns)
    assert lang is not None and lang.get(f"{{{ns['w']}}}val") == "ja-JP"


def test_struct_role_extraction_unit() -> None:
    converter = PdfToDocxConverter()

    class DummyReader:
        def __init__(self) -> None:
            page_one = DictionaryObject()
            page_one.indirect_reference = IndirectObject(1, 0, None)
            page_two = DictionaryObject()
            page_two.indirect_reference = IndirectObject(2, 0, None)
            self.pages = [page_one, page_two]

            struct_elem_one = DictionaryObject(
                {
                    NameObject("/S"): NameObject("/H1"),
                    NameObject("/Pg"): IndirectObject(1, 0, None),
                }
            )
            struct_elem_two = DictionaryObject(
                {
                    NameObject("/S"): NameObject("/P"),
                    NameObject("/Pg"): IndirectObject(1, 0, None),
                }
            )
            struct_tree = DictionaryObject(
                {
                    NameObject("/Type"): NameObject("/StructTreeRoot"),
                    NameObject("/K"): ArrayObject([struct_elem_one, struct_elem_two]),
                }
            )
            self.trailer = DictionaryObject(
                {
                    NameObject("/Root"): DictionaryObject(
                        {NameObject("/StructTreeRoot"): struct_tree}
                    )
                }
            )

    roles, global_roles, tagged = converter._extract_struct_roles(DummyReader())
    assert tagged is True
    assert roles[0] == ["H1", "P"]
    assert global_roles == []


def test_convert_document_invalid_page_index(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with pdf_path.open("wb") as fh:
        writer.write(fh)

    options = ConversionOptions(page_numbers=[5])
    with pytest.raises(ValueError):
        convert_document(pdf_path, options=options)


def test_convert_requires_output_for_document(tmp_path: Path) -> None:
    page = Page(
        number=0,
        width=100,
        height=100,
        text_blocks=[
            TextBlock(text="Doc", bbox=BoundingBox(0, 0, 10, 10)),
        ],
        images=[],
        lines=[],
    )
    document = PdfDocument(pages=[page])

    converter = PdfToDocxConverter()
    with pytest.raises(ValueError):
        converter.convert(document)


def test_detects_and_emits_footnotes(tmp_path: Path) -> None:
    page = Page(
        number=0,
        width=200,
        height=200,
        text_blocks=[
            TextBlock(
                text="Body text",
                bbox=BoundingBox(40, 150, 160, 170),
                font_name="Helvetica",
                font_size=12,
            ),
            TextBlock(
                text="1",
                bbox=BoundingBox(160, 155, 168, 172),
                font_name="Helvetica",
                font_size=8,
                superscript=True,
            ),
            TextBlock(
                text="1 Footnote details",
                bbox=BoundingBox(40, 20, 180, 40),
                font_name="Helvetica",
                font_size=8,
            ),
        ],
        images=[],
        lines=[],
    )
    document = PdfDocument(pages=[page])

    output = tmp_path / "footnotes.docx"
    PdfToDocxConverter().convert(document, output)

    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with ZipFile(output) as archive:
        assert "word/footnotes.xml" in archive.namelist()
        footnote_root = ElementTree.parse(archive.open("word/footnotes.xml")).getroot()
        doc_root = ElementTree.parse(archive.open("word/document.xml")).getroot()
    references = doc_root.findall(".//w:footnoteReference", namespace)
    assert references
    footnote_texts = [
        (node.text or "")
        for node in footnote_root.findall(
            ".//w:footnote[@w:id!='0'][@w:id!='1']//w:t", namespace
        )
    ]
    assert any("Footnote details" in text for text in footnote_texts)


def test_can_move_footnotes_to_endnotes(tmp_path: Path) -> None:
    page = Page(
        number=0,
        width=200,
        height=200,
        text_blocks=[
            TextBlock(
                text="Body text",
                bbox=BoundingBox(40, 150, 160, 170),
                font_name="Helvetica",
                font_size=12,
            ),
            TextBlock(
                text="1",
                bbox=BoundingBox(160, 155, 168, 172),
                font_name="Helvetica",
                font_size=8,
                superscript=True,
            ),
            TextBlock(
                text="1 Footnote details",
                bbox=BoundingBox(40, 20, 180, 40),
                font_name="Helvetica",
                font_size=8,
            ),
        ],
        images=[],
        lines=[],
    )
    document = PdfDocument(pages=[page])

    output = tmp_path / "endnotes.docx"
    options = ConversionOptions(footnotes_as_endnotes=True)
    PdfToDocxConverter(options).convert(document, output)

    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with ZipFile(output) as archive:
        assert "word/endnotes.xml" in archive.namelist()
        assert "word/footnotes.xml" not in archive.namelist()
        endnote_root = ElementTree.parse(archive.open("word/endnotes.xml")).getroot()
        doc_root = ElementTree.parse(archive.open("word/document.xml")).getroot()
    references = doc_root.findall(".//w:endnoteReference", namespace)
    assert references
    endnote_texts = [
        (node.text or "")
        for node in endnote_root.findall(
            ".//w:endnote[@w:id!='0'][@w:id!='1']//w:t", namespace
        )
    ]
    assert any("Footnote details" in text for text in endnote_texts)


def test_form_fields_render_into_tables(tmp_path: Path) -> None:
    page = Page(
        number=0,
        width=400,
        height=400,
        text_blocks=[],
        images=[],
        lines=[],
        form_fields=[
            FormField(
                bbox=BoundingBox(40, 340, 220, 370),
                field_type="text",
                label="Full Name",
                value="Alice Example",
            ),
            FormField(
                bbox=BoundingBox(40, 290, 220, 320),
                field_type="checkbox",
                label="Newsletter",
                checked=True,
                value="Yes",
            ),
            FormField(
                bbox=BoundingBox(40, 240, 220, 270),
                field_type="checkbox",
                label="Terms Accepted",
                checked=False,
            ),
            FormField(
                bbox=BoundingBox(40, 190, 220, 220),
                field_type="dropdown",
                label="Country",
                value="Canada",
                options=["United States", "Canada", "Mexico"],
            ),
            FormField(
                bbox=BoundingBox(40, 140, 220, 170),
                field_type="signature",
                label="Signature",
            ),
        ],
    )
    document = PdfDocument(pages=[page])

    output = tmp_path / "forms.docx"
    PdfToDocxConverter().convert(document, output)

    with ZipFile(output) as archive:
        doc_xml = archive.read("word/document.xml").decode("utf-8")

    assert doc_xml.count("<w:tbl") >= 5
    assert "Full Name" in doc_xml
    assert "Alice Example" in doc_xml
    assert "☑" in doc_xml
    assert "☐" in doc_xml
    assert "Selected: Canada" in doc_xml
    assert "Options: United States, Canada, Mexico" in doc_xml
    assert "____________________" in doc_xml


def test_pdf_annotations_emit_comments(tmp_path: Path) -> None:
    annotation = PdfAnnotation(
        bbox=BoundingBox(40, 120, 180, 140),
        text="This is a note",
        author="Alice",
    )
    page = Page(
        number=0,
        width=200,
        height=200,
        text_blocks=[
            TextBlock(
                text="Commented paragraph",
                bbox=BoundingBox(40, 120, 180, 140),
                font_name="Helvetica",
                font_size=12,
            )
        ],
        images=[],
        lines=[],
        annotations=[annotation],
    )
    document = PdfDocument(pages=[page])

    output = tmp_path / "comments.docx"
    PdfToDocxConverter().convert(document, output)

    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with ZipFile(output) as archive:
        assert "word/comments.xml" in archive.namelist()
        comments_root = ElementTree.parse(archive.open("word/comments.xml")).getroot()
        doc_root = ElementTree.parse(archive.open("word/document.xml")).getroot()
    comment_nodes = comments_root.findall(".//w:comment", namespace)
    assert comment_nodes
    authors = {
        node.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}author")
        for node in comment_nodes
    }
    assert "Alice" in authors
    comment_text = " ".join(
        (node.text or "") for node in comments_root.findall(".//w:comment//w:t", namespace)
    )
    assert "This is a note" in comment_text
    assert doc_root.findall(".//w:commentReference", namespace)


def test_mathml_to_omml_generates_minimal_omml() -> None:
    mathml = (
        "<math xmlns='http://www.w3.org/1998/Math/MathML'>"
        "<mrow><mi>x</mi><mo>+</mo><mi>y</mi></mrow>"
        "</math>"
    )
    omml = mathml_to_omml(mathml)
    assert omml is not None
    assert "oMath" in omml


def test_block_to_equation_uses_mathml_for_equation() -> None:
    block = TextBlock(
        text=(
            "<math xmlns='http://www.w3.org/1998/Math/MathML'>"
            "<mrow><mi>a</mi><mo>=</mo><mfrac><mi>b</mi><mi>c</mi></mfrac></mrow>"
            "</math>"
        ),
        bbox=BoundingBox(0, 0, 40, 20),
        font_name="Times-Roman",
        font_size=12,
        role="Formula",
    )
    result = block_to_equation(block, [], set(), [])
    assert result.equation.omml is not None
    assert "oMath" in result.equation.omml
    assert result.used_image_index is None


def test_block_to_equation_falls_back_to_picture_when_no_mathml() -> None:
    block = TextBlock(
        text="",
        bbox=BoundingBox(0, 0, 40, 20),
        font_name="Times-Roman",
        font_size=12,
        role="Formula",
    )
    image = Image(
        data=_png_bytes(10, 10),
        bbox=BoundingBox(0, 0, 40, 20),
        mime_type="image/png",
    )
    result = block_to_equation(block, [image], set(), [])
    assert result.used_image_index == 0
    assert result.equation.picture is not None
    assert result.equation.picture.description == "Equation"


def test_build_equation_paragraph_adds_hidden_alt_text_for_math() -> None:
    mathml = "<math xmlns='http://www.w3.org/1998/Math/MathML'><mi>z</mi></math>"
    omml = mathml_to_omml(mathml)
    equation = Equation(omml=omml, description="Equation")
    paragraph = build_equation_paragraph(
        equation,
        RelationshipManager(),
        BookmarkState(),
    )
    xml = ElementTree.tostring(paragraph, encoding="unicode")
    assert f"{{{XML_NS['w']}}}vanish" in xml or "w:vanish" in xml
    assert "oMath" in xml


def test_build_equation_paragraph_preserves_alt_text_for_pictures() -> None:
    block = TextBlock(
        text="",
        bbox=BoundingBox(0, 0, 40, 20),
        font_name="Times-Roman",
        font_size=12,
        role="Formula",
    )
    image = Image(
        data=_png_bytes(8, 8),
        bbox=BoundingBox(0, 0, 40, 20),
        mime_type="image/png",
    )
    detection = block_to_equation(block, [image], set(), [])
    paragraph = build_equation_paragraph(
        detection.equation,
        RelationshipManager(),
        BookmarkState(),
    )
    xml = ElementTree.tostring(paragraph, encoding="unicode")
    assert f"{{{XML_NS['w']}}}vanish" in xml or "w:vanish" in xml

def test_extract_vector_graphics_rectangles_produce_lines_and_paths():
    writer = PdfWriter()
    page = writer.add_blank_page(width=200, height=200)
    content = StreamObject()
    drawing = b"q 2 w 0 0 0 RG 0 0 1 rg 40 50 80 60 re B Q"
    content._data = drawing
    content[NameObject("/Length")] = NumberObject(len(drawing))
    page[NameObject("/Contents")] = content
    buffer = BytesIO()
    writer.write(buffer)
    buffer.seek(0)
    reader = PdfReader(buffer)
    lines, paths = extract_vector_graphics(reader.pages[0], reader)
    assert len(lines) == 4
    assert len(paths) == 1
    vector_path = paths[0]
    assert vector_path.is_rectangle
    assert vector_path.fill_color is not None


def test_path_to_picture_rasterizes_shape():
    triangle = Path(
        subpaths=[[(0.0, 0.0), (40.0, 0.0), (20.0, 30.0), (0.0, 0.0)]],
        stroke_color=(0.0, 0.0, 0.0),
        fill_color=(1.0, 0.0, 0.0),
        stroke_width=1.0,
        fill_rule="nonzero",
        stroke_alpha=1.0,
        fill_alpha=1.0,
        is_rectangle=False,
    )
    picture = path_to_picture(triangle)
    assert picture.mime_type == "image/png"
    assert picture.width == pytest.approx(40.0)
    assert picture.height == pytest.approx(30.0)
    assert picture.data.startswith(b"\x89PNG")


def test_collect_page_placements_applies_path_background():
    block = TextBlock(
        text="Hello",
        bbox=BoundingBox(left=20.0, bottom=20.0, right=80.0, top=60.0),
    )
    path = Path(
        subpaths=[
            [
                (10.0, 10.0),
                (90.0, 10.0),
                (90.0, 70.0),
                (10.0, 70.0),
                (10.0, 10.0),
            ]
        ],
        fill_color=(0.5, 0.5, 0.5),
        stroke_color=None,
        stroke_width=None,
        fill_rule="nonzero",
        stroke_alpha=0.0,
        fill_alpha=1.0,
        is_rectangle=True,
    )
    page = Page(
        number=0,
        width=200.0,
        height=200.0,
        text_blocks=[block],
        images=[],
        lines=[],
        paths=[path],
    )
    placements = collect_page_placements(page, strip_whitespace=False)
    assert block.background_color == "808080"
    assert len(placements) == 1
    assert placements[0][2] == "text"
