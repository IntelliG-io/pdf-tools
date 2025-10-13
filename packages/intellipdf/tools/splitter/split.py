"""Plugin adapter exposing the legacy split utilities through the new registry."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from pypdf import PdfWriter

from ...core.parser import PDFParser
from ...core.utils import get_logger
from ...core.validator import ensure_output_parent
from ..common.interfaces import BaseTool
from ..common.pipeline import register_tool
from .utils import build_output_filename, normalize_pages, parse_page_ranges

LOGGER = get_logger("intellipdf.tools.split")


def _write_document(writer: PdfWriter, destination: Path, metadata: dict | None) -> None:
    if metadata:
        writer.add_metadata(metadata)
    with destination.open("wb") as output_stream:
        writer.write(output_stream)


@register_tool("split")
class SplitTool(BaseTool):
    name = "split"

    def run(self) -> list[Path]:
        context = self.context
        parser = context.ensure_parser()
        output_dir = context.output_path
        if output_dir is None:
            raise ValueError("Split tool requires an output directory")
        output_dir.mkdir(parents=True, exist_ok=True)

        mode = context.config.get("mode", "range")
        ranges = context.config.get("ranges")
        pages = context.config.get("pages")

        total_pages = parser.page_count()
        reader = parser.reader
        metadata = dict(parser.metadata())
        base_name = parser.source.stem

        results: list[Path] = []
        if mode == "range":
            page_ranges = parse_page_ranges(ranges, total_pages=total_pages)
            for page_range in page_ranges:
                writer = PdfWriter()
                for page_num in range(page_range.start, page_range.end + 1):
                    writer.add_page(reader.pages[page_num - 1])
                destination = output_dir / build_output_filename(base_name, page_range)
                LOGGER.debug(
                    "Writing pages %s-%s to %s", page_range.start, page_range.end, destination
                )
                _write_document(writer, destination, metadata)
                results.append(destination)
        elif mode == "pages":
            if pages is None:
                raise ValueError("pages argument is required when mode='pages'")
            page_numbers = normalize_pages(pages, total_pages=total_pages)
            for page_number in page_numbers:
                writer = PdfWriter()
                writer.add_page(reader.pages[page_number - 1])
                destination = output_dir / build_output_filename(base_name, page_number)
                LOGGER.debug("Writing page %s to %s", page_number, destination)
                _write_document(writer, destination, metadata)
                results.append(destination)
        else:  # pragma: no cover - defensive branch
            raise ValueError(f"Unsupported split mode: {mode}")

        context.resources["result"] = results
        return results


@register_tool("extract")
class ExtractTool(BaseTool):
    name = "extract"

    def run(self) -> Path:
        context = self.context
        parser: PDFParser = context.ensure_parser()
        output = context.output_path
        if output is None:
            raise ValueError("Extract tool requires an output path")
        output = ensure_output_parent(output)

        pages: Sequence[int | str] | None = context.config.get("pages")
        if pages is None:
            raise ValueError("pages configuration is required for extraction")

        reader = parser.reader
        total_pages = parser.page_count()
        metadata = dict(parser.metadata())
        writer = PdfWriter()
        for page_number in normalize_pages(pages, total_pages=total_pages):
            writer.add_page(reader.pages[page_number - 1])

        LOGGER.debug("Extracting pages %s to %s", pages, output)
        _write_document(writer, output, metadata)
        context.resources["result"] = output
        return output
