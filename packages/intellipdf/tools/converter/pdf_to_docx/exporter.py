"""PDF → DOCX exporter registered with the IntelliPDF tool registry."""

from __future__ import annotations

from typing import Any

from ....core.utils import get_logger
from ....pdf2docx.converter import ConversionMetadata, ConversionOptions, ConversionResult
from ....pdf2docx import convert_pdf_to_docx
from ...common.interfaces import BaseTool
from ...common.pipeline import register_tool
from .parser_adapter import PdfToDocxParserAdapter

LOGGER = get_logger("intellipdf.tools.convert.docx")


@register_tool("convert_docx")
class PdfToDocxExporter(BaseTool):
    name = "convert_docx"

    def run(self) -> ConversionResult:
        context = self.context
        parser = None
        if context.input_path is not None:
            parser = context.ensure_parser()
            adapter = PdfToDocxParserAdapter(parser)
            context.resources.setdefault("metadata", adapter.metadata())
        elif context.parser is not None:
            parser = context.parser

        options = self._ensure_options(context.config.get("options"))
        metadata = self._ensure_metadata(context.config.get("metadata"))

        input_document = context.config.get("document")
        if input_document is None:
            if context.input_path is None and parser is None:
                raise ValueError("Conversion requires either an input path or document object")
            input_document = context.input_path or context.config.get("input")

        output = context.output_path or context.config.get("output")

        LOGGER.debug("Converting %s to DOCX at %s", input_document, output)
        result = convert_pdf_to_docx(
            input_document,
            output,
            options=options,
            metadata=metadata,
        )
        context.resources["result"] = result
        if output is None:
            context.output_path = result.output_path
        return result

    @staticmethod
    def _ensure_options(value: Any) -> ConversionOptions | None:
        if value is None or isinstance(value, ConversionOptions):
            return value
        if isinstance(value, dict):
            return ConversionOptions(**value)
        raise TypeError("options must be a ConversionOptions instance or mapping")

    @staticmethod
    def _ensure_metadata(value: Any) -> ConversionMetadata | None:
        if value is None or isinstance(value, ConversionMetadata):
            return value
        if isinstance(value, dict):
            return ConversionMetadata(**value)
        raise TypeError("metadata must be a ConversionMetadata instance or mapping")
