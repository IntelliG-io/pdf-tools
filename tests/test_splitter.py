from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable

import pytest
from pypdf import PdfReader

from intellipdf import (
    extract_document_pages,
    get_split_info,
    split_document,
    validate_split_pdf,
)
from intellipdf.tools.splitter import splitter
from intellipdf.tools.splitter.exceptions import InvalidPageRangeError, PDFValidationError
from intellipdf.tools.splitter.optimizers import optimize_pdf
from intellipdf.tools.splitter.utils import (
    build_output_filename,
    coerce_path,
    normalize_pages,
    parse_page_ranges,
)


def test_split_pdf_by_ranges(sample_pdf: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "ranges"
    outputs = split_document(
        sample_pdf,
        output_dir,
        mode="range",
        ranges="1-2, 3-5",
    )

    assert len(outputs) == 2
    assert all(path.exists() for path in outputs)

    first = PdfReader(str(outputs[0]))
    second = PdfReader(str(outputs[1]))

    assert len(first.pages) == 2
    assert len(second.pages) == 3
    assert first.metadata.get("/Title") == "Sample"


def test_split_pdf_by_pages(sample_pdf: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "pages"
    outputs = split_document(
        sample_pdf,
        output_dir,
        mode="pages",
        pages=[1, 3, 5],
    )

    assert {path.name for path in outputs} == {
        "sample_page_1.pdf",
        "sample_page_3.pdf",
        "sample_page_5.pdf",
    }

    for path in outputs:
        reader = PdfReader(str(path))
        assert len(reader.pages) == 1
        assert reader.metadata.get("/Producer") == "intellipdf-tests"


def test_extract_pages(sample_pdf: Path, tmp_path: Path) -> None:
    output = tmp_path / "extract.pdf"
    result = extract_document_pages(sample_pdf, [2, 4], output)

    reader = PdfReader(str(result))
    assert len(reader.pages) == 2
    assert reader.metadata.get("/Title") == "Sample"


def test_invalid_pages_raises(sample_pdf: Path, tmp_path: Path) -> None:
    with pytest.raises(InvalidPageRangeError):
        split_document(sample_pdf, tmp_path, mode="pages", pages=[0])

    with pytest.raises(InvalidPageRangeError):
        split_document(sample_pdf, tmp_path, mode="range", ranges="10-12")


def test_validation_and_info(sample_pdf: Path, empty_pdf: Path) -> None:
    assert validate_split_pdf(sample_pdf) is True
    info = get_split_info(sample_pdf)
    assert info["pages"] == 5
    assert info["metadata"]["/Title"] == "Sample"

    with pytest.raises(PDFValidationError):
        validate_split_pdf(empty_pdf)


def test_range_and_page_parsers(sample_pdf: Path) -> None:
    reader = PdfReader(str(sample_pdf))
    ranges = parse_page_ranges("1-2,5", total_pages=len(reader.pages))
    assert ranges[0].start == 1 and ranges[0].end == 2
    assert ranges[1].start == 5 and ranges[1].end == 5

    pages = normalize_pages(["1", 2, "5"], total_pages=len(reader.pages))
    assert pages == [1, 2, 5]

    tuple_ranges = parse_page_ranges([(1, 3), "5", 4], total_pages=len(reader.pages))
    assert [r.start for r in tuple_ranges] == [1, 5, 4]

    name = build_output_filename("my file", tuple_ranges[0])
    assert name == "my_file_pages_1-3.pdf"

    single = build_output_filename("base", 2)
    assert single == "base_page_2.pdf"

    with pytest.raises(InvalidPageRangeError):
        parse_page_ranges(None, total_pages=len(reader.pages))

    with pytest.raises(InvalidPageRangeError):
        parse_page_ranges([""], total_pages=len(reader.pages))

    with pytest.raises(InvalidPageRangeError):
        normalize_pages([0], total_pages=len(reader.pages))

    path = coerce_path(sample_pdf)
    assert path.exists()


def test_optimize_pdf_branches(monkeypatch: pytest.MonkeyPatch, sample_pdf: Path, tmp_path: Path) -> None:
    # Simulate qpdf availability and successful execution
    calls: list[list[str]] = []

    def fake_which(_name: str) -> str:
        return "/usr/bin/qpdf"

    def fake_run(command: Iterable[str], check: bool, stdout, stderr) -> None:  # type: ignore[override]
        calls.append(list(command))
        dest = Path(command[-1])
        dest.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr("intellipdf.tools.splitter.optimizers.shutil.which", fake_which)
    monkeypatch.setattr("intellipdf.tools.splitter.optimizers.subprocess.run", fake_run)

    destination = tmp_path / "optimised.pdf"
    assert optimize_pdf(sample_pdf, destination) is True
    assert calls and calls[0][0] == "/usr/bin/qpdf"


def test_optimize_pdf_handles_missing_and_failure(
    monkeypatch: pytest.MonkeyPatch, sample_pdf: Path, tmp_path: Path
) -> None:
    monkeypatch.setattr("intellipdf.tools.splitter.optimizers.shutil.which", lambda _: None)
    destination = tmp_path / "skip.pdf"
    destination.write_bytes(b"data")
    assert optimize_pdf(sample_pdf, destination) is False

    def fake_which(_: str) -> str:
        return "/usr/bin/qpdf"

    def fake_run(command: Iterable[str], check: bool, stdout, stderr) -> None:  # type: ignore[override]
        raise subprocess.CalledProcessError(returncode=1, cmd=list(command))

    monkeypatch.setattr("intellipdf.tools.splitter.optimizers.shutil.which", fake_which)
    monkeypatch.setattr("intellipdf.tools.splitter.optimizers.subprocess.run", fake_run)
    assert optimize_pdf(sample_pdf, destination) is False


def test_split_pdf_respects_environment(monkeypatch: pytest.MonkeyPatch, sample_pdf: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "env"
    monkeypatch.setenv("INTELLIPDF_SPLIT_OPTIMIZE", "1")

    def fake_optimize(src: Path, dst: Path) -> bool:  # type: ignore[override]
        dst.write_bytes(Path(src).read_bytes())
        return True

    monkeypatch.setattr(splitter, "optimize_pdf", fake_optimize)
    outputs = split_document(sample_pdf, output_dir, mode="pages", pages=[1])
    assert outputs[0].exists()


def test_validate_pdf_error_branches(monkeypatch: pytest.MonkeyPatch, sample_pdf: Path) -> None:
    with pytest.raises(PDFValidationError):
        validate_split_pdf(sample_pdf.parent / "missing.pdf")

    class DummyReader:
        def __init__(self, *_: object, **__: object) -> None:
            self.is_encrypted = True
            self.pages = [object()]

        def decrypt(self, _: str) -> None:
            return None

    monkeypatch.setattr("intellipdf.tools.splitter.validators.PdfReader", lambda path: DummyReader())
    assert validate_split_pdf(sample_pdf) is True
