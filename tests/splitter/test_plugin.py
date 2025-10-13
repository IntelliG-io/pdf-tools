from __future__ import annotations

from pathlib import Path

from intellipdf.tools import load_builtin_plugins
from intellipdf.tools.common.interfaces import ConversionContext
from intellipdf.tools.common.pipeline import registry


def setup_module(module):
    load_builtin_plugins()


def test_split_tool_creates_files(sample_pdf: Path, tmp_path: Path) -> None:
    context = ConversionContext(
        input_path=sample_pdf,
        output_path=tmp_path,
        config={"mode": "pages", "pages": [1]},
    )
    tool = registry.create("split", context)
    result = tool.run()
    assert len(result) == 1
    assert result[0].exists()


def test_extract_tool_outputs_single_file(sample_pdf: Path, tmp_path: Path) -> None:
    output = tmp_path / "extracted.pdf"
    context = ConversionContext(
        input_path=sample_pdf,
        output_path=output,
        config={"pages": [1, 2]},
    )
    tool = registry.create("extract", context)
    result = tool.run()
    assert result.exists()
    assert result == output
