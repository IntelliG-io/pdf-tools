from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from intellipdf import ConversionMetadata

from apps.backend.app.main import app


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


def test_perform_pdf_to_docx_conversion_uses_simple_pipeline(
    monkeypatch, tmp_path: Path
) -> None:
    from apps.backend.app import main

    captured: dict[str, object] = {}

    class DummyResult:
        def __init__(self, output_path: Path) -> None:
            self.output_path = output_path
            self.page_count = 1
            self.paragraph_count = 1
            self.word_count = 1
            self.line_count = 1

    class DummyConverter:
        def __init__(self, options) -> None:  # pragma: no cover - simple wiring
            captured["options"] = options

        def convert(self, input_document, output_path, *, metadata):
            captured["input_document"] = Path(input_document)
            captured["output_path"] = Path(output_path)
            captured["metadata"] = metadata
            destination = Path(output_path)
            destination.write_bytes(b"PK\x03\x04mock")
            return DummyResult(destination)

    monkeypatch.setattr(
        "apps.backend.app.main.PdfToDocxConverter",
        DummyConverter,
    )

    input_path = tmp_path / "source.pdf"
    output_path = tmp_path / "result.docx"
    input_path.write_bytes(b"%PDF")

    metadata = ConversionMetadata(title="Example")

    result = main._perform_pdf_to_docx_conversion(
        input_path,
        output_path,
        [0, 2],
        metadata,
    )

    assert isinstance(result, DummyResult)
    assert captured["input_document"] == input_path
    assert captured["output_path"] == output_path
    assert captured["metadata"] is metadata

    options = captured["options"]
    assert options.page_numbers == [0, 2]
    assert options.strip_whitespace is False
    assert options.stream_pages is False
    assert options.include_outline_toc is False
    assert options.generate_toc_field is False
    assert options.footnotes_as_endnotes is False


def test_pdf_to_docx_rejects_invalid_options(sample_pdf: Path) -> None:
    files = {
        "file": ("sample.pdf", sample_pdf.read_bytes(), "application/pdf"),
    }

    response = client.post("/convert/pdf-to-docx", data={"options": "not-json"}, files=files)

    assert response.status_code == 400
    assert "options must be valid JSON" in response.text
