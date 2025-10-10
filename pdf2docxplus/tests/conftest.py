from __future__ import annotations

import sys
from pathlib import Path


# Ensure the project root is importable when tests are executed from the
# package's ``tests`` directory. Pytest adds the tests directory to
# ``sys.path`` which means sibling packages are not automatically resolved
# unless we manually expose the repository root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from pypdf import PdfWriter


@pytest.fixture()
def sample_pdf(tmp_path: Path) -> Path:
    path = tmp_path / "sample.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.add_metadata(
        {
            "/Title": "Test Document",
            "/Author": "Jane Doe",
            "/Subject": "Testing",
            "/Keywords": "pdf,docx",
            "/Creator": "pytest",
            "/Producer": "pdf2docxplus",
            "/CreationDate": "D:20230501120000+01'00'",
            "/ModDate": "D:20230502130000+01'00'",
            "/Custom": "Value",
        }
    )
    with path.open("wb") as fp:
        writer.write(fp)
    return path
