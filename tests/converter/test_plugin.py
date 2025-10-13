from __future__ import annotations

from pathlib import Path

from intellipdf.tools import load_builtin_plugins
from intellipdf.tools.common.interfaces import ConversionContext
from intellipdf.tools.common.pipeline import registry


def setup_module(module):
    load_builtin_plugins()


def test_convert_docx_tool(sample_pdf: Path, tmp_path: Path) -> None:
    output = tmp_path / "output.docx"
    context = ConversionContext(
        input_path=sample_pdf,
        output_path=output,
        config={"options": None, "metadata": None},
    )
    tool = registry.create("convert_docx", context)
    result = tool.run()
    assert result.output_path == output
    assert output.exists()
