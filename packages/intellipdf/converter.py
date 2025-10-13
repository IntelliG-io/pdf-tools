"""Unified conversion pipeline orchestrating parser, interpreter, layout, and DOCX export."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Iterable, Sequence
from zipfile import ZipFile, BadZipFile

from .core.parser import PDFParser, ParsedDocument
from .exporters.docx.generator import DocxGenerator
from .tools.common.interfaces import ConversionContext
from .tools.converter.pdf_to_docx.converter.types import (
    ConversionMetadata,
    ConversionOptions,
    ConversionResult,
)
from .tools.converter.pdf_to_docx.converter.pipeline import PipelineLogger
from .tools.converter.pdf_to_docx.interpreter import PDFContentInterpreter, PageContent
from .tools.converter.pdf_to_docx.layout_analyzer import IntermediateRepresentation, LayoutAnalyzer
from .tools.converter.pdf_to_docx.converter.metadata import merge_metadata as _merge_metadata

__all__ = ["ConversionPipeline", "convert_pdf_to_docx"]


@dataclass(slots=True)
class _StageTimings:
    parse_ms: float = 0.0
    interpret_ms: float = 0.0
    analyse_ms: float = 0.0
    export_ms: float = 0.0

    def per_page(self, pages: int) -> dict[str, float]:
        safe = max(1, pages)
        return {
            "parse_ms_per_page": self.parse_ms / safe,
            "interpret_ms_per_page": self.interpret_ms / safe,
            "analyse_ms_per_page": self.analyse_ms / safe,
            "export_ms_per_page": self.export_ms / safe,
        }


class ConversionPipeline:
    """Run the end-to-end PDF → DOCX conversion using discrete stages."""

    def __init__(
        self,
        *,
        options: ConversionOptions | None = None,
        metadata: ConversionMetadata | None = None,
        parser_factory: type[PDFParser] = PDFParser,
        interpreter_factory: type[PDFContentInterpreter] = PDFContentInterpreter,
        analyzer_factory: type[LayoutAnalyzer] = LayoutAnalyzer,
        docx_generator: DocxGenerator | None = None,
    ) -> None:
        self.options = options or ConversionOptions()
        self.metadata = metadata
        self._parser_factory = parser_factory
        self._interpreter_factory = interpreter_factory
        self._analyzer_factory = analyzer_factory
        self._generator = docx_generator or DocxGenerator()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def run(
        self,
        input_document: str | Path,
        output_path: str | Path | None = None,
        *,
        context: ConversionContext | None = None,
    ) -> ConversionResult:
        """Convert *input_document* into DOCX stored at *output_path*."""

        source_path = Path(input_document)
        if not source_path.exists():
            raise FileNotFoundError(f"Input PDF not found: {source_path}")
        destination = self._resolve_output_path(source_path, output_path)

        timings = _StageTimings()
        logger = PipelineLogger()
        resources = context.resources if context is not None else {}

        # -- Stage 1: Parse -------------------------------------------------
        parse_start = perf_counter()
        parser = self._parser_factory(source_path)
        parsed = parser.parse()
        timings.parse_ms = (perf_counter() - parse_start) * 1000.0
        page_numbers = self._resolve_page_numbers(parsed.page_count, self.options.page_numbers)
        logger.advance(
            f"Parsed '{source_path.name}' ({parsed.page_count} pages) in {timings.parse_ms:.1f} ms."
        )
        resources["parsed_document"] = parsed

        # -- Stage 2: Interpret content streams -----------------------------
        interpret_start = perf_counter()
        interpreter = self._interpreter_factory(parsed)
        page_contents = self._interpret_pages(interpreter, page_numbers)
        timings.interpret_ms = (perf_counter() - interpret_start) * 1000.0
        glyphs_total = sum(len(content.glyphs) for content in page_contents)
        images_total = sum(len(content.images) for content in page_contents)
        logger.advance(
            f"Decoded {len(page_numbers)} selected pages -> glyphs={glyphs_total}, images={images_total} "
            f"in {timings.interpret_ms:.1f} ms."
        )
        resources["page_contents"] = page_contents

        # -- Stage 3: Layout analysis --------------------------------------
        analyse_start = perf_counter()
        analyzer = self._analyzer_factory(self.options)
        ir = analyzer.analyse(parsed, contents=page_contents)
        if self.metadata is not None:
            ir.document.metadata = _merge_metadata(ir.document.metadata, self.metadata)
            log_entries.append("Applied metadata overrides to IR document metadata.")
        timings.analyse_ms = (perf_counter() - analyse_start) * 1000.0
        logger.advance(
            f"Extracted layout into {ir.document.page_count} section(s) with "
            f"{sum(len(section.elements) for section in ir.document.sections)} elements "
            f"in {timings.analyse_ms:.1f} ms."
        )
        resources["intermediate_representation"] = ir

        # -- Stage 4: Export DOCX ------------------------------------------
        export_start = perf_counter()
        generation_result = self._generator.generate(ir, destination)
        timings.export_ms = (perf_counter() - export_start) * 1000.0
        self._basic_validation(generation_result.output_path)
        logger.advance(
            f"Generated DOCX '{generation_result.output_path.name}' "
            f"in {timings.export_ms:.1f} ms (paragraphs={generation_result.stats.paragraphs}, "
            f"words={generation_result.stats.words})."
        )

        # -- Stage 5: Summary & metrics ------------------------------------
        total_duration = timings.parse_ms + timings.interpret_ms + timings.analyse_ms + timings.export_ms
        logger.advance(
            f"Conversion complete in {total_duration:.1f} ms "
            f"(pages={len(page_numbers)}, tagged={ir.tagged_pdf})."
        )

        while logger.remaining():
            logger.advance()

        metrics = {
            "parse_ms": timings.parse_ms,
            "interpret_ms": timings.interpret_ms,
            "analyse_ms": timings.analyse_ms,
            "export_ms": timings.export_ms,
            "total_ms": total_duration,
            **timings.per_page(len(page_numbers)),
        }
        resources["conversion_metrics"] = metrics
        resources["docx_generation_metadata"] = generation_result.metadata
        log_records = tuple(logger.records)
        resources["conversion_log"] = log_records

        stats = generation_result.stats
        return ConversionResult(
            output_path=generation_result.output_path.resolve(),
            page_count=len(page_numbers),
            paragraph_count=stats.paragraphs,
            word_count=stats.words,
            line_count=stats.lines,
            tagged_pdf=ir.tagged_pdf,
            log=log_records,
        )

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _resolve_output_path(source: Path, destination: str | Path | None) -> Path:
        if destination is None:
            return source.with_suffix(".docx")
        resolved = Path(destination)
        if resolved.suffix.lower() != ".docx":
            resolved = resolved.with_suffix(".docx")
        resolved.parent.mkdir(parents=True, exist_ok=True)
        return resolved

    @staticmethod
    def _resolve_page_numbers(total_pages: int, requested: Sequence[int] | None) -> list[int]:
        if requested is None:
            return list(range(total_pages))
        page_numbers: list[int] = []
        for index in requested:
            if index < 0 or index >= total_pages:
                raise ValueError(f"Page index {index} out of bounds for document with {total_pages} pages")
            page_numbers.append(index)
        return page_numbers

    def _interpret_pages(
        self,
        interpreter: PDFContentInterpreter,
        page_numbers: Iterable[int],
    ) -> list[PageContent]:
        contents: list[PageContent] = []
        for index in page_numbers:
            contents.append(interpreter.interpret_page(index))
        return contents

    @staticmethod
    def _basic_validation(output_path: Path) -> None:
        try:
            with ZipFile(output_path, "r") as archive:
                # Ensure mandatory parts exist.
                archive.getinfo("word/document.xml")
                archive.getinfo("[Content_Types].xml")
        except (BadZipFile, KeyError) as exc:
            raise RuntimeError(f"Generated DOCX appears invalid: {exc}") from exc


# ---------------------------------------------------------------------- #
# Public convenience function
# ---------------------------------------------------------------------- #


def convert_pdf_to_docx(
    input_document: str | Path,
    output_path: str | Path | None = None,
    *,
    options: ConversionOptions | None = None,
    metadata: ConversionMetadata | None = None,
    context: ConversionContext | None = None,
) -> ConversionResult:
    """High level helper that converts *input_document* into a DOCX package."""

    pipeline = ConversionPipeline(options=options, metadata=metadata)
    return pipeline.run(input_document, output_path, context=context)
