from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from apps.backend.app.main import app


client = TestClient(app)


def test_pdf_to_docx_conversion_endpoint(sample_pdf: Path) -> None:
    payload = {
        "options": json.dumps({"pageNumbers": [1, 3], "streamPages": False}),
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


def test_pdf_to_docx_applies_conservative_defaults(
    monkeypatch, sample_pdf: Path
) -> None:
    captured: dict[str, object] = {}

    def fake_convert(input_document, output_path, *, options, metadata):
        captured["options"] = options
        output = Path(output_path)
        output.write_bytes(b"PK\x03\x04mock")

        class Result:
            def __init__(self, output_path: Path) -> None:
                self.output_path = output_path
                self.page_count = 1
                self.paragraph_count = 1
                self.word_count = 1
                self.line_count = 1

        return Result(output)

    monkeypatch.setattr("apps.backend.app.main.convert_pdf_to_docx", fake_convert)

    files = {
        "file": ("sample.pdf", sample_pdf.read_bytes(), "application/pdf"),
    }

    response = client.post("/convert/pdf-to-docx", data={}, files=files)

    assert response.status_code == 200
    assert captured

    options = captured["options"]
    assert options.strip_whitespace is False
    assert options.stream_pages is False
    assert options.include_outline_toc is False
    assert options.generate_toc_field is False


def test_pdf_to_docx_rejects_invalid_options(sample_pdf: Path) -> None:
    files = {
        "file": ("sample.pdf", sample_pdf.read_bytes(), "application/pdf"),
    }

    response = client.post("/convert/pdf-to-docx", data={"options": "not-json"}, files=files)

    assert response.status_code == 400
    assert "options must be valid JSON" in response.text
