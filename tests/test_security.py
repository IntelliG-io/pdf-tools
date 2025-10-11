from __future__ import annotations

from pathlib import Path

import pytest
from pypdf import PdfReader

from intellipdf.security import (
    PdfSecurityError,
    is_pdf_encrypted,
    protect_pdf,
    unprotect_pdf,
)


def test_protect_pdf_encrypts_document(sample_pdf: Path, tmp_path: Path) -> None:
    output = tmp_path / "secured.pdf"
    protect_pdf(sample_pdf, output, "secret")

    reader = PdfReader(str(output))
    assert reader.is_encrypted is True
    assert is_pdf_encrypted(output) is True
    assert reader.decrypt("secret") != 0
    outline_titles = [item.get("/Title") for item in reader.outline or []]
    assert "Section 1" in outline_titles


def test_protect_pdf_refuses_already_encrypted(sample_pdf: Path, tmp_path: Path) -> None:
    first = tmp_path / "first.pdf"
    protect_pdf(sample_pdf, first, "secret")

    with pytest.raises(PdfSecurityError):
        protect_pdf(first, tmp_path / "second.pdf", "another")


def test_unprotect_pdf_decrypts_document(sample_pdf: Path, tmp_path: Path) -> None:
    protected = tmp_path / "protected.pdf"
    unprotected = tmp_path / "unprotected.pdf"

    protect_pdf(sample_pdf, protected, "secret")
    result = unprotect_pdf(protected, unprotected, "secret")

    reader = PdfReader(str(result))
    assert reader.is_encrypted is False
    metadata = reader.metadata
    assert metadata is None or metadata.get("/Title") == "Sample"
    outline_titles = [item.get("/Title") for item in reader.outline or []]
    assert "Section 1" in outline_titles


def test_unprotect_pdf_requires_correct_password(sample_pdf: Path, tmp_path: Path) -> None:
    protected = tmp_path / "protected.pdf"
    protect_pdf(sample_pdf, protected, "secret")

    with pytest.raises(PdfSecurityError):
        unprotect_pdf(protected, tmp_path / "output.pdf", "wrong")
