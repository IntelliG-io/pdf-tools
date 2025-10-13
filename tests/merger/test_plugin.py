from __future__ import annotations

from pathlib import Path

from intellipdf.tools import load_builtin_plugins
from intellipdf.tools.common.interfaces import ConversionContext
from intellipdf.tools.common.pipeline import registry


def setup_module(module):
    load_builtin_plugins()


def test_merge_tool(sample_pdfs: list[Path], tmp_path: Path) -> None:
    output = tmp_path / "merged.pdf"
    context = ConversionContext(output_path=output, config={"inputs": sample_pdfs})
    tool = registry.create("merge", context)
    result = tool.run()
    assert result == output
    assert output.exists()
