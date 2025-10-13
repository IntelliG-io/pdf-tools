"""Plugin exposing PDF merge capabilities through the registry."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping, Sequence

from ...core.utils import get_logger
from ...merge.exceptions import PdfMergeError
from ...merge.merger import merge_pdfs
from ..common.interfaces import BaseTool
from ..common.pipeline import register_tool

LOGGER = get_logger("intellipdf.tools.merge")


@register_tool("merge")
class MergeTool(BaseTool):
    name = "merge"

    def run(self) -> Path:
        context = self.context
        inputs: Iterable[str | Path] | None = context.config.get("inputs")
        if inputs is None:
            if context.input_path is None:
                raise PdfMergeError("No input PDFs provided")
            inputs = [context.input_path]

        output = context.output_path
        if output is None:
            raise PdfMergeError("Merge tool requires an output path")

        metadata = context.config.get("metadata", True)
        document_info: Mapping[str, object] | None = context.config.get("document_info")
        bookmarks: Sequence[str] | None = context.config.get("bookmarks")

        inputs_list = list(inputs)
        LOGGER.debug("Merging %d input(s) into %s", len(inputs_list), output)
        result = merge_pdfs(
            inputs_list,
            output,
            metadata=metadata,
            document_info=document_info,
            bookmarks=bookmarks,
        )
        context.resources["result"] = result
        return result
