from __future__ import annotations

from pathlib import Path

from intellipdf.tools import load_builtin_plugins
from intellipdf.tools.common.interfaces import ConversionContext
from intellipdf.tools.common.pipeline import registry


def setup_module(module):
    load_builtin_plugins()


def test_compress_tool(sample_pdf: Path, tmp_path: Path) -> None:
    output = tmp_path / "compressed.pdf"
    context = ConversionContext(
        input_path=sample_pdf,
        output_path=output,
        config={"level": "low"},
    )
    tool = registry.create("compress", context)
    result = tool.run()
    assert result.output_path == output
    assert result.compressed_size <= result.original_size
