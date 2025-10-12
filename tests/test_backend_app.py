from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from intellipdf import ConversionMetadata

from apps.backend.app.main import PipelineResult, _perform_pdf_to_docx_conversion, app


client = TestClient(app)


def test_pdf_to_docx_conversion_endpoint(sample_pdf: Path) -> None:
    payload = {
        "options": json.dumps({"pageNumbers": [1, 3]}),
    }
    files = {
        "file": ("sample.pdf", sample_pdf.read_bytes(), "application/pdf"),
    }

    response = client.post("/convert/pdf-to-docx", data=payload, files=files)

    assert response.status_code == 200
    assert (
        response.headers.get("content-type")
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    disposition = response.headers.get("content-disposition", "")
    assert "sample.docx" in disposition
    assert response.headers.get("x-intellipdf-docx-page-count") == "2"
    assert response.content[:2] == b"PK"


def test_perform_pdf_to_docx_conversion_emits_diagnostics(tmp_path: Path) -> None:
    def _create_pdf(path: Path, text: str) -> None:
        from pypdf import PdfWriter
        from pypdf.generic import (
            DictionaryObject,
            NameObject,
            NumberObject,
            StreamObject,
        )

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
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})}
        )
        content_bytes = f"BT /F1 12 Tf 72 100 Td ({text}) Tj ET".encode("utf-8")
        stream = StreamObject()
        stream[NameObject("/Length")] = NumberObject(len(content_bytes))
        stream._data = content_bytes
        stream_ref = writer._add_object(stream)
        page[NameObject("/Contents")] = stream_ref
        with path.open("wb") as handle:
            writer.write(handle)

    input_path = tmp_path / "source.pdf"
    output_path = tmp_path / "result.docx"
    _create_pdf(input_path, "Hello pipeline")

    metadata = ConversionMetadata(title="Pipeline Title")

    result = _perform_pdf_to_docx_conversion(
        input_path,
        output_path,
        [0],
        metadata,
    )

    assert isinstance(result, PipelineResult)
    assert result.conversion.output_path == output_path.resolve()
    diagnostics = result.diagnostics.as_dict()
    assert diagnostics["pdf-parsing"]["selected_pages"] == [0]
    assert diagnostics["layout-analysis"]["fonts"] == ["Helvetica"]
    assert diagnostics["docx-packaging"]["metadata_title"] == "Pipeline Title"
    assert "word/document.xml" in diagnostics["docx-packaging"]["docx_parts"]


def test_pdf_to_docx_rejects_invalid_options(sample_pdf: Path) -> None:
    files = {
        "file": ("sample.pdf", sample_pdf.read_bytes(), "application/pdf"),
    }

    response = client.post("/convert/pdf-to-docx", data={"options": "not-json"}, files=files)

    assert response.status_code == 400
    assert "options must be valid JSON" in response.text
