from pathlib import Path
from types import SimpleNamespace

import pytest
from pypdf import PdfReader, PdfWriter

from intellipdf import compress_document
from intellipdf.tools.compressor import (
    CompressionResult,
    compress_pdf,
    get_compression_info,
    validate_pdf,
)
from intellipdf.tools.compressor import info as compress_info
from intellipdf.tools.compressor import compressor
from intellipdf.tools.compressor import utils as compress_utils
from intellipdf.tools.compressor.compressor import CompressionLevel, CompressionResult as ResultType
from intellipdf.tools.compressor.exceptions import CompressionError, InvalidPDFError
from intellipdf.tools.compressor.optimizers import (
    Backend,
    BackendType,
    build_ghostscript_command,
    build_qpdf_command,
    detect_backend,
    run_backend,
)


@pytest.fixture()
def simple_pdf(tmp_path: Path) -> Path:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_metadata({
        "/Title": "Sample Document",
        "/Author": "intellipdf",
    })
    path = tmp_path / "sample.pdf"
    with path.open("wb") as fh:
        writer.write(fh)
    return path


def test_compress_pdf_creates_output(simple_pdf: Path, tmp_path: Path) -> None:
    output = tmp_path / "compressed.pdf"
    result = compress_pdf(simple_pdf, output, level="medium", post_validate=False)

    assert isinstance(result, CompressionResult)
    assert output.exists()
    assert result.compressed_size > 0

    reader = PdfReader(str(output))
    assert reader.metadata.get("/Title") == "Sample Document"


def test_compress_document_helper(simple_pdf: Path, tmp_path: Path) -> None:
    output = tmp_path / "compressed.pdf"
    result = compress_document(simple_pdf, output, level="medium")
    assert result.output_path == output


def test_compress_pdf_supports_high_level(simple_pdf: Path, tmp_path: Path) -> None:
    output = tmp_path / "high.pdf"
    result = compress_pdf(simple_pdf, output, level="high", post_validate=False)
    assert result.output_path == output
    assert result.level == "high"


def test_compress_pdf_invalid_level(simple_pdf: Path, tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        compress_pdf(simple_pdf, tmp_path / "out.pdf", level="invalid")


def test_validate_pdf_rejects_non_pdf(tmp_path: Path) -> None:
    bogus = tmp_path / "not.pdf"
    bogus.write_text("not a pdf")

    with pytest.raises(InvalidPDFError):
        validate_pdf(bogus, use_external=False)


def test_compress_pdf_post_validate(simple_pdf: Path, tmp_path: Path) -> None:
    output = tmp_path / "validated.pdf"
    result = compress_pdf(simple_pdf, output, post_validate=True)
    assert result.output_path.exists()
    validate_pdf(result.output_path, use_external=False)


def test_get_compression_info_reports_metrics(simple_pdf: Path) -> None:
    info = get_compression_info(simple_pdf)

    assert info.file_size_bytes == simple_pdf.stat().st_size
    assert info.image_count == 0
    assert info.potential_savings_bytes >= 0


def test_compression_error_when_missing_input(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        compress_pdf(tmp_path / "missing.pdf", tmp_path / "out.pdf")


def test_compress_pdf_with_backend(monkeypatch: pytest.MonkeyPatch, simple_pdf: Path, tmp_path: Path) -> None:
    backend = Backend(BackendType.QPDF, executable="/usr/bin/qpdf")

    def fake_select() -> Backend:
        return backend

    def fake_run(_backend: Backend, source: Path, destination: Path, level: str) -> None:
        destination.write_bytes(Path(source).read_bytes())

    monkeypatch.setattr(compressor, "_select_backend", fake_select)
    monkeypatch.setattr(compressor, "run_backend", fake_run)

    output = tmp_path / "backend.pdf"
    result = compress_pdf(simple_pdf, output, level="low", post_validate=True)

    assert result.backend == BackendType.QPDF
    assert result.output_path.exists()


def test_compress_pdf_backend_failure(monkeypatch: pytest.MonkeyPatch, simple_pdf: Path, tmp_path: Path) -> None:
    backend = Backend(BackendType.QPDF, executable="/usr/bin/qpdf")

    def fake_select() -> Backend:
        return backend

    def fake_run(_backend: Backend, source: Path, destination: Path, level: str) -> None:
        raise RuntimeError("backend failure")

    monkeypatch.setattr(compressor, "_select_backend", fake_select)
    monkeypatch.setattr(compressor, "run_backend", fake_run)

    output = tmp_path / "fallback.pdf"
    result = compress_pdf(simple_pdf, output, level="medium", post_validate=False)

    assert result.backend == BackendType.QPDF
    assert result.output_path.exists()


def test_compress_pdf_reports_errors(monkeypatch: pytest.MonkeyPatch, simple_pdf: Path, tmp_path: Path) -> None:
    monkeypatch.setattr(compressor, "_select_backend", lambda: None)

    def failing_copy(*_: object, **__: object) -> None:
        raise OSError("copy failed")

    monkeypatch.setattr(compressor.shutil, "copy2", failing_copy)

    with pytest.raises(CompressionError):
        compress_pdf(simple_pdf, tmp_path / "fail.pdf")


def test_compression_result_properties() -> None:
    level = CompressionLevel("medium", image_quality=80, downsample_ratio=0.75, recompress_streams=True)
    result = ResultType(
        input_path=Path("/input.pdf"),
        output_path=Path("/output.pdf"),
        level=level.name,
        original_size=200,
        compressed_size=100,
        backend=BackendType.QPDF,
    )

    assert result.bytes_saved == 100
    assert result.compression_ratio == 0.5


def test_compression_result_handles_zero_original_size() -> None:
    result = ResultType(
        input_path=Path("/input.pdf"),
        output_path=Path("/output.pdf"),
        level="low",
        original_size=0,
        compressed_size=0,
        backend=None,
    )

    assert result.bytes_saved == 0
    assert result.compression_ratio == 1.0


def test_compress_utils_helpers(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path = compress_utils.resolve_path(tmp_path)
    assert path == tmp_path.resolve()

    target = tmp_path / "nested" / "file.pdf"
    compress_utils.ensure_parent_dir(target)
    assert target.parent.exists()

    monkeypatch.setattr(compress_utils.shutil, "which", lambda cmd: "/usr/bin/qpdf" if cmd == "qpdf" else None)
    assert compress_utils.which(["qpdf", "gs"]) == "/usr/bin/qpdf"

    called: list[list[str]] = []

    def fake_run(command: list[str], **_: object) -> SimpleNamespace:
        called.append(command)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(compress_utils.subprocess, "run", fake_run)
    result = compress_utils.run_subprocess(["echo", "hello"], check=True)
    assert called and called[0] == ["echo", "hello"]
    assert result.returncode == 0

    assert compress_utils.sizeof_fmt(512) == "512.0 bytes"
    assert compress_utils.sizeof_fmt(2048).endswith("KiB")

    merged = compress_utils.merge_dicts({"a": "1"}, {"b": "2"}, {"a": "3"})
    assert merged == {"a": "3", "b": "2"}


def test_validate_pdf_triggers_external_tool(monkeypatch: pytest.MonkeyPatch, simple_pdf: Path) -> None:
    calls: list[list[str]] = []

    def fake_detect(*_: object, **__: object) -> Backend:
        return Backend(BackendType.QPDF, "/usr/bin/qpdf")

    def fake_run(command: list[str], **_: object) -> SimpleNamespace:
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("intellipdf.tools.compressor.validators.detect_backend", fake_detect)
    monkeypatch.setattr("intellipdf.tools.compressor.validators.run_subprocess", fake_run)

    validate_pdf(simple_pdf, use_external=True)
    assert calls and calls[0][0].endswith("qpdf")


def test_compression_info_helpers() -> None:
    class FakeImage:
        def __init__(self) -> None:
            self.width = 144
            self.height = 144
            self.data = b"data"
            self.name = "I1"

    class FakePage:
        mediabox = SimpleNamespace(width=144, height=144)

        def __init__(self) -> None:
            self.images = [FakeImage()]

        def get(self, key: str, default=None):  # noqa: D401 - behaviour mimics dict
            if key == "/Resources":
                return {"/XObject": {"I1": SimpleNamespace(get_object=lambda: SimpleNamespace(_data=b"orig"))}}
            return default

    reader = SimpleNamespace(pages=[FakePage()])

    image_count, average_dpi = compress_info._estimate_image_dpi(reader)
    assert image_count == 1
    assert average_dpi is not None

    assert compress_info._estimate_potential_savings(1000, 0) == 50
    assert compress_info._estimate_potential_savings(1000, 50) <= 600


def test_optimizer_command_builders(tmp_path: Path) -> None:
    source = tmp_path / "input.pdf"
    output = tmp_path / "output.pdf"
    source.touch()

    qpdf_cmd = build_qpdf_command("qpdf", source, output, "medium")
    assert qpdf_cmd[0] == "qpdf"
    assert "--linearize" in qpdf_cmd

    ghostscript_cmd = build_ghostscript_command("gs", source, output, "low")
    assert ghostscript_cmd[0] == "gs"
    assert any(arg.startswith("-sOutputFile=") for arg in ghostscript_cmd)


def test_run_backend_and_detection(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    commands: list[list[str]] = []

    def fake_run(command: list[str]) -> SimpleNamespace:
        commands.append(command)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("intellipdf.tools.compressor.optimizers.run_subprocess", fake_run)

    backend = Backend(BackendType.QPDF, "qpdf")
    run_backend(backend, tmp_path / "in.pdf", tmp_path / "out.pdf", "high")
    backend = Backend(BackendType.GHOSTSCRIPT, "gs")
    run_backend(backend, tmp_path / "in.pdf", tmp_path / "out.pdf", "medium")

    assert len(commands) == 2

    with pytest.raises(ValueError):
        run_backend(SimpleNamespace(type="unknown", executable="noop"), tmp_path / "in.pdf", tmp_path / "out.pdf", "low")

    monkeypatch.setattr("intellipdf.tools.compressor.optimizers.which", lambda execs: None)
    assert detect_backend(preferred=[BackendType.QPDF]) is None

    monkeypatch.setattr(
        "intellipdf.tools.compressor.optimizers.which",
        lambda execs: "/usr/bin/gs" if "gs" in execs else None,
    )
    detected = detect_backend()
    assert detected is not None and detected.type is BackendType.GHOSTSCRIPT
