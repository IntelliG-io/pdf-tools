from __future__ import annotations

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, NameObject, NumberObject

from intellipdf.core.parser import PDFParser


def _write_sample_pdf(path, *, use_xref_stream: bool = False) -> None:
    writer = PdfWriter()
    if use_xref_stream:
        if hasattr(writer, "use_xref_stream"):
            writer.use_xref_stream = True  # type: ignore[attr-defined]
        else:
            setattr(writer, "_use_xref_stream", True)
    page = writer.add_blank_page(width=200, height=400)
    stream = DecodedStreamObject()
    stream.set_data(b"q\nQ\n")
    page[NameObject("/Contents")] = stream
    page[NameObject("/Resources")] = DictionaryObject()
    writer.add_metadata({"/Title": "Test Document", "/Author": "IntelliPDF"})
    with path.open("wb") as handle:
        writer.write(handle)


def test_pdf_parser_builds_parsed_document(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    _write_sample_pdf(pdf_path)

    parser = PDFParser(pdf_path)
    startxref, xref_kind = parser.locate_cross_reference()
    assert startxref > 0
    assert xref_kind == "table"
    document = parser.parse()

    raw_offsets, trailers = parser._parse_cross_reference(
        parser.reader, pdf_path.read_bytes(), document.startxref
    )

    assert trailers
    trailer_info = parser.read_trailer()

    assert document.version.startswith("1.")
    assert document.page_count == 1
    assert document.metadata["/Title"] == "Test Document"
    assert parser.metadata()["/Author"] == "IntelliPDF"
    assert document.startxref > 0

    page = document.pages[0]
    assert page.geometry.media_box == (0.0, 0.0, 200.0, 400.0)
    assert page.content_streams
    assert page.contents.strip() == b"q\nQ"
    assert page.object_ref is not None
    assert raw_offsets.get(page.object_ref) is not None
    assert document.object_offsets.get(page.object_ref) is not None

    assert trailer_info["root_ref"] is not None
    root_ref = trailer_info["root_ref"]
    assert trailer_info["entries"].get("/Root") == {"$ref": root_ref}
    assert trailer_info["size"] is not None and trailer_info["size"] >= 1
    assert document.trailer == trailer_info["entries_dereferenced"]

    catalog_info = parser.read_document_catalog()
    assert catalog_info["catalog"]["/Type"] == "/Catalog"
    assert catalog_info.get("catalog_ref") == root_ref
    assert catalog_info.get("pages_ref")
    assert catalog_info.get("pages")["/Type"] == "/Pages"
    assert catalog_info.get("pages_count") == 1
    pages_summary = catalog_info.get("pages_tree_summary")
    assert pages_summary
    assert pages_summary["type"] == "/Pages"
    assert pages_summary.get("count") == 1
    assert pages_summary.get("kids_count") == 1
    assert pages_summary.get("kids")
    assert pages_summary["kids"][0]["type"] == "/Page"

    assert catalog_info.get("pages_leaf_count") == 1
    leaf_entries = catalog_info.get("pages_leaves")
    assert isinstance(leaf_entries, list)
    assert len(leaf_entries) == 1
    assert leaf_entries[0]["type"] == "/Page"
    assert leaf_entries[0]["index"] == 0
    assert leaf_entries[0].get("ref") == page.object_ref

    resolved = document.resolver.resolve(page.object_ref)
    assert resolved is not None
    assert page.resources == {}


def test_pdf_parser_handles_xref_stream(tmp_path):
    pdf_path = tmp_path / "xref_stream.pdf"
    _write_sample_pdf(pdf_path, use_xref_stream=True)

    parser = PDFParser(pdf_path)
    startxref, xref_kind = parser.locate_cross_reference()
    assert startxref > 0
    assert xref_kind == "stream"
    document = parser.parse()

    raw_offsets, trailers = parser._parse_cross_reference(
        parser.reader, pdf_path.read_bytes(), document.startxref
    )

    assert document.object_offsets
    page = document.pages[0]
    assert page.object_ref is not None
    assert raw_offsets.get(page.object_ref) is not None
    assert document.object_offsets.get(page.object_ref) is not None

    trailer_info = parser.read_trailer()
    assert trailer_info["sources"][0] == "xref_stream"


def test_pdf_parser_collects_incremental_xref_sections(tmp_path):
    pdf_path = tmp_path / "incremental.pdf"
    _write_sample_pdf(pdf_path)

    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()
    writer.clone_reader_document_root(reader)
    writer.add_metadata({"/Subject": "Incremental"})
    with pdf_path.open("rb+") as handle:
        writer.write(handle, incremental=True)

    parser = PDFParser(pdf_path)
    document = parser.parse()
    raw_offsets, trailers = parser._parse_cross_reference(
        parser.reader, pdf_path.read_bytes(), document.startxref
    )

    page = document.pages[0]
    assert page.object_ref is not None
    assert raw_offsets.get(page.object_ref) is not None
    assert len(trailers) >= 1
    trailer_info = parser.read_trailer()
    assert trailer_info["root_ref"] is not None


def test_pdf_parser_traverses_nested_pages_tree(tmp_path):
    pdf_path = tmp_path / "nested.pdf"

    writer = PdfWriter()
    for _ in range(3):
        writer.add_blank_page(width=200, height=200)

    pages_root = writer._root_object[NameObject("/Pages")]
    kids = pages_root[NameObject("/Kids")]
    first_ref, second_ref, third_ref = kids[0], kids[1], kids[2]

    subtree = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Pages"),
            NameObject("/Count"): NumberObject(2),
            NameObject("/Parent"): pages_root.indirect_reference,
            NameObject("/Kids"): ArrayObject([second_ref, third_ref]),
        }
    )
    subtree_ref = writer._add_object(subtree)

    pages_root[NameObject("/Kids")] = ArrayObject([first_ref, subtree_ref])
    pages_root[NameObject("/Count")] = NumberObject(3)

    for child_ref in subtree[NameObject("/Kids")]:
        child_page = child_ref.get_object()
        child_page[NameObject("/Parent")] = subtree_ref

    with pdf_path.open("wb") as handle:
        writer.write(handle)

    parser = PDFParser(pdf_path)
    catalog_info = parser.read_document_catalog()

    assert catalog_info.get("pages_leaf_count") == 3
    leaf_entries = catalog_info.get("pages_leaves")
    assert isinstance(leaf_entries, list)
    assert len(leaf_entries) == 3
    assert [entry.get("index") for entry in leaf_entries] == [0, 1, 2]
    assert all(entry.get("ref") for entry in leaf_entries)

    document = parser.parse()
    assert document.page_count == 3

    parsed_refs = [page.object_ref for page in document.pages]
    summary_refs = [entry.get("ref") for entry in leaf_entries]
    assert parsed_refs == summary_refs
