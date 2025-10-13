"""Plugin exposing compression helper through the registry."""

from __future__ import annotations

from ...compress import CompressionResult, compress_pdf
from ...core.utils import get_logger
from ..common.interfaces import BaseTool
from ..common.pipeline import register_tool

LOGGER = get_logger("intellipdf.tools.compress")


@register_tool("compress")
class CompressTool(BaseTool):
    name = "compress"

    def run(self) -> CompressionResult:
        context = self.context
        if context.input_path is None or context.output_path is None:
            raise ValueError("Compression requires input and output paths")

        level = context.config.get("level")
        if level is None:
            level = context.config.get("compression_level", "medium")
        LOGGER.debug(
            "Compressing %s to %s with level %s",
            context.input_path,
            context.output_path,
            level,
        )
        result = compress_pdf(context.input_path, context.output_path, level=level)
        context.resources["result"] = result
        return result
