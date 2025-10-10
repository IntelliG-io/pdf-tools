from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Callable

import pytest

from intellipdf import (
    get_merge_info,
    merge_documents,
    merge_pdfs,
    optimize_merge_pdf,
    validate_merge_pdf,
)
from intellipdf.merge import merger
from intellipdf.merge.exceptions import PdfMergeError, PdfValidationError
from intellipdf.merge import utils as merge_utils


def test_merge_pdfs_creates_output(tmp_path: Path, sample_pdfs: list[Path]) -> None:
    output = tmp_path / "merged.pdf"

    result = merge_pdfs(sample_pdfs, output)

    assert result == output
    assert output.exists()

    info = get_merge_info(output)
    assert info.num_pages == 2
    assert info.metadata.get("/Title") == "Document One"


def test_merge_documents_helper(tmp_path: Path, sample_pdfs: list[Path]) -> None:
    output = tmp_path / "merged.pdf"
    result = merge_documents(sample_pdfs, output)
    assert result == output


def test_merge_pdfs_no_inputs(tmp_path: Path) -> None:
    with pytest.raises(PdfMergeError):
        merge_pdfs([], tmp_path / "out.pdf")


@pytest.mark.parametrize("qpdf_present", [False, True])
def test_optimize_pdf(
    monkeypatch: pytest.MonkeyPatch,
    pdf_factory: Callable[[str, str | None], Path],
    tmp_path: Path,
    qpdf_present: bool,
) -> None:
    input_pdf = pdf_factory("input.pdf")
    output_pdf = tmp_path / "optimized.pdf"

    if not qpdf_present:
        monkeypatch.setattr(
            "intellipdf.merge.optimizers._qpdf_available",
            lambda: None,
        )
    else:
        def fake_run(
            command: list[str],
            capture_output: bool,
            text: bool,
            check: bool,
        ) -> SimpleNamespace:
            output_pdf.write_bytes(input_pdf.read_bytes())
            return SimpleNamespace(returncode=0, stderr="")

        monkeypatch.setattr(
            "intellipdf.merge.optimizers._qpdf_available",
            lambda: "qpdf",
        )
        monkeypatch.setattr(
            "intellipdf.merge.optimizers.subprocess.run",
            fake_run,
        )

    result = optimize_merge_pdf(input_pdf, output_pdf)

    assert result == output_pdf
    assert output_pdf.exists()
    assert output_pdf.read_bytes() == input_pdf.read_bytes()


def test_validate_pdf_success(pdf_factory: Callable[[str, str | None], Path]) -> None:
    pdf_path = pdf_factory("doc.pdf")
    assert validate_merge_pdf(pdf_path)


def test_validate_pdf_failure(tmp_path: Path) -> None:
    invalid_path = tmp_path / "not.pdf"
    invalid_path.write_text("not a pdf")
    with pytest.raises(Exception):
        validate_merge_pdf(invalid_path)


def test_get_pdf_info(pdf_factory: Callable[[str, str | None], Path]) -> None:
    pdf_path = pdf_factory("info.pdf")
    info = get_merge_info(pdf_path)
    assert info.num_pages == 1
    assert "/Producer" in info.metadata
    assert info.metadata.get("/Title") is None


def test_validate_pdf_empty_document(tmp_path: Path) -> None:
    empty = tmp_path / "empty.pdf"
    from pypdf import PdfWriter

    writer = PdfWriter()
    with empty.open("wb") as handle:
        writer.write(handle)

    with pytest.raises(PdfValidationError):
        validate_merge_pdf(empty)


def test_merge_utils_helpers(tmp_path: Path) -> None:
    unresolved = "~/../"
    resolved = merge_utils.ensure_path(unresolved)
    assert isinstance(resolved, Path)

    paths = merge_utils.ensure_iterable([tmp_path, str(tmp_path / "other.pdf")])
    assert all(isinstance(p, Path) for p in paths)


def test_load_reader_handles_encrypted(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    sample = tmp_path / "sample.pdf"
    sample.write_bytes(b"%PDF-1.4\n")

    class DummyReader:
        def __init__(self, *_: object, **__: object) -> None:
            self.is_encrypted = True
            self.pages = []

        def decrypt(self, password: str) -> None:
            self.decrypt_called = password  # type: ignore[attr-defined]

    monkeypatch.setattr("intellipdf.merge.merger.PdfReader", lambda path: DummyReader())

    reader = merger._load_reader(sample)
    assert isinstance(reader, DummyReader)
    assert getattr(reader, "decrypt_called") == ""
