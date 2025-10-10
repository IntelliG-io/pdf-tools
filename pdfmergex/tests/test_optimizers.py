from __future__ import annotations

from pathlib import Path
from typing import Callable
from types import SimpleNamespace

import pytest

from pdfmergex.optimizers import optimize_pdf


@pytest.mark.parametrize("qpdf_present", [False, True])
def test_optimize_pdf(
    pdf_factory: Callable[[str, str | None], Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    qpdf_present: bool,
) -> None:
    input_pdf = pdf_factory("input.pdf")
    output_pdf = tmp_path / "optimized.pdf"

    if not qpdf_present:
        monkeypatch.setattr(
            "pdfmergex.optimizers._qpdf_available",
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
            "pdfmergex.optimizers._qpdf_available",
            lambda: "qpdf",
        )
        monkeypatch.setattr(
            "pdfmergex.optimizers.subprocess.run",
            fake_run,
        )

    result = optimize_pdf(input_pdf, output_pdf)

    assert result == output_pdf
    assert output_pdf.exists()
    assert output_pdf.read_bytes() == input_pdf.read_bytes()
