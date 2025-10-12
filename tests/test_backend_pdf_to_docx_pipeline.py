from __future__ import annotations
from pathlib import Path

import pytest

from intellipdf import ConversionMetadata

from apps.backend.app.main import _perform_pdf_to_docx_conversion


def _create_pdf(path: Path, texts: list[str]) -> None:
    from pypdf import PdfWriter
    from pypdf.generic import (
        DictionaryObject,
        NameObject,
        NumberObject,
        StreamObject,
    )

    writer = PdfWriter()
    for text in texts:
        page = writer.add_blank_page(width=200, height=200)
        font_dict = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        font_ref = writer._add_object(font_dict)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})}
        )
        escaped = text.replace("(", r"\(").replace(")", r"\)")
        content_bytes = f"BT /F1 12 Tf 72 100 Td ({escaped}) Tj ET".encode("utf-8")
        stream = StreamObject()
        stream[NameObject("/Length")] = NumberObject(len(content_bytes))
        stream._data = content_bytes
        stream_ref = writer._add_object(stream)
        page[NameObject("/Contents")] = stream_ref
    with path.open("wb") as handle:
        writer.write(handle)


def test_pipeline_layout_diagnostics(tmp_path: Path) -> None:
    source = tmp_path / "multi.pdf"
    output = tmp_path / "result.docx"
    _create_pdf(source, ["First page", "Second page"])

    result = _perform_pdf_to_docx_conversion(
        source,
        output,
        [1],
        ConversionMetadata(author="Tester"),
    )

    diagnostics = result.diagnostics.as_dict()
    parsing = diagnostics["pdf-parsing"]
    layout = diagnostics["layout-analysis"]
    packaging = diagnostics["docx-packaging"]

    assert parsing["page_count"] == 2
    assert parsing["selected_pages"] == [1]
    assert layout["pages"] == 1
    assert layout["fonts"] == ["Helvetica"]
    assert layout["images"] == 0
    assert layout["paragraph_estimate"] >= 1
    assert packaging["metadata_title"] is None
    assert result.conversion.page_count == 1
 

def test_pipeline_invalid_page_numbers(tmp_path: Path) -> None:
    source = tmp_path / "single.pdf"
    output = tmp_path / "result.docx"
    _create_pdf(source, ["Only page"])

    with pytest.raises(ValueError):
        _perform_pdf_to_docx_conversion(
            source,
            output,
            [5],
            None,
        )

