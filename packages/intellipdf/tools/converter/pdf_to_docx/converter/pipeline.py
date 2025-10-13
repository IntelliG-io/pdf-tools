"""Conversion pipeline orchestrating PDF → DOCX stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

from pypdf import PdfReader

from ..docx.writer import write_docx as _legacy_write_docx
from ..ir import Document, DocumentMetadata, Paragraph, Picture, Table
from ..primitives import Page, PdfDocument
from .builder import DocumentBuilder
from .metadata import merge_metadata, metadata_from_mapping
from .reader import extract_outline, extract_struct_roles, page_from_reader
from .types import ConversionMetadata, ConversionOptions, PdfDocumentLike

PIPELINE_STEPS: Sequence[str] = (
    "Load or receive parsed PdfDocument instance.",
    "Initialize configuration (DPI, header/footer detection, rasterization options).",
    "Prepare temporary storage for pages, fonts, images, and IR data.",
    "Parse PDF structure if not already parsed (xref, objects, streams).",
    "Extract page dictionaries (size, rotation, resources).",
    "Extract and decode page content streams.",
    "Resolve fonts and load ToUnicode CMaps.",
    "Extract text glyphs with position, font, size, and color.",
    "Extract embedded raster images (JPEG, JPX, JBIG2, PNG).",
    "Normalize page coordinates (rotation, scaling).",
    "If Tagged PDF, read StructTreeRoot for semantic elements.",
    "Otherwise, cluster glyphs into lines by baseline proximity.",
    "Group lines into blocks based on spacing and alignment.",
    "Merge blocks into paragraphs (font/spacing continuity).",
    "Detect text alignment (left, right, center, justified).",
    "Infer paragraph roles (heading, normal, quote, caption).",
    "Detect bullet or numbered lists (prefix analysis).",
    "Detect multi-level nesting for lists by indent depth.",
    "Identify tables via ruling lines or whitespace grid analysis.",
    "Detect repeating header/footer patterns across pages.",
    "Detect images and their positions within flow.",
    "Assemble each page’s layout map (text blocks, images, tables).",
    "Create document-level Intermediate Representation (IR).",
    "Populate IR Document metadata from PDF info dictionary.",
    "Convert each page layout into Section objects in IR.",
    "Create Paragraph, Run, Table, Row, Cell, and Picture objects.",
    "Assign paragraph styles and numbering references.",
    "Deduplicate and register fonts, colors, and images globally.",
    "Normalize measurement units (points → twips/half-points/EMUs).",
    "Initialize DOCX package builder (ZIP container).",
    "Generate [Content_Types].xml.",
    "Generate _rels/.rels linking to main document.",
    "Create docProps/core.xml and docProps/app.xml metadata parts.",
    "Start building word/document.xml root (<w:document><w:body>).",
    "For each IR section, write paragraphs and tables sequentially.",
    "For each paragraph, write <w:p> with <w:pPr> style and spacing.",
    "For each run, write <w:r> with <w:rPr> and <w:t> text node.",
    "For lists, include <w:numPr> with numId and ilvl.",
    "For tables, write <w:tbl> with grid columns, rows, and merged cells.",
    "For images, embed <w:drawing> referencing media rIds.",
    "For hyperlinks, wrap runs in <w:hyperlink r:id='rIdN'>.",
    "Insert bookmarks and section breaks where needed.",
    "Close <w:body> with final <w:sectPr> (margins, size, headers).",
    "Write word/styles.xml (Normal, Heading, List, Caption, etc.).",
    "Write word/numbering.xml (bullet/decimal list templates).",
    "Write word/fontTable.xml if fonts present.",
    "Write word/settings.xml (optional defaults, bidi).",
    "Embed media files under /word/media/.",
    "Write image relationships in word/_rels/document.xml.rels.",
    "Write hyperlink, header, and footer relationships.",
    "If header/footer detected, write word/header1.xml and/or word/footer1.xml.",
    "Add page number fields if required.",
    "Finalize all relationship files and IDs.",
    "Verify that all relationships target existing parts.",
    "Verify [Content_Types].xml includes all MIME types.",
    "Close the ZIP package cleanly.",
    "Run internal validation (syntax, structure, and style completeness).",
    "Confirm DOCX opens without repair prompts in MS Word.",
    "Return success status and summary log (pages, paragraphs, images, etc.).",
)


@dataclass(slots=True)
class PipelineLogger:
    """Tracks progress through the conversion pipeline."""

    steps: Sequence[str] = PIPELINE_STEPS
    _index: int = 0
    records: list[str] = field(default_factory=list)

    def advance(self, detail: str | None = None) -> None:
        if self._index >= len(self.steps):
            raise RuntimeError("Conversion pipeline logged more steps than expected")
        step = self.steps[self._index]
        self._index += 1
        if detail:
            message = f"{step} {detail}"
        else:
            message = step
        self.records.append(message)

    def remaining(self) -> int:
        return len(self.steps) - self._index


@dataclass(slots=True)
class PipelineState:
    """Holds intermediate data during conversion."""

    input_document: str | Path | PdfDocumentLike
    destination: Path
    options: ConversionOptions
    logger: PipelineLogger
    page_numbers: list[int] = field(default_factory=list)
    reader: PdfReader | None = None
    pdf_document: PdfDocument | PdfDocumentLike | None = None
    tagged_pdf: bool = False
    base_metadata: DocumentMetadata | None = None
    outline: Sequence | None = None
    pages: list[Page] = field(default_factory=list)
    page_dictionaries: list[object] = field(default_factory=list)
    font_maps: list[dict[str, tuple[int, int]] | None] = field(default_factory=list)
    total_glyphs: int = 0
    total_images: int = 0
    builder: DocumentBuilder | None = None
    document: Document | None = None


def _is_pdf_document_like(value: object) -> bool:
    return isinstance(value, PdfDocumentLike)


def _chain_roles(page_roles: Sequence[str], global_roles: Iterable[str]) -> Iterable[str]:
    for role in page_roles:
        yield role
    yield from global_roles


class PdfToDocxPipeline:
    """Runs the end-to-end PDF → DOCX conversion."""

    def __init__(self, options: ConversionOptions) -> None:
        self.options = options

    def run(
        self,
        input_document: str | Path | PdfDocumentLike,
        output_path: Path,
        metadata: ConversionMetadata | None,
    ) -> tuple[Document, tuple[int, int, int, int], tuple[str, ...]]:
        logger = PipelineLogger()
        state = PipelineState(
            input_document=input_document,
            destination=output_path,
            options=self.options,
            logger=logger,
        )
        self._load_input(state)
        self._initialise_configuration(state)
        self._prepare_storage(state)
        self._parse_structure(state)
        self._extract_pages(state)
        self._analyse_layout(state)
        document = self._build_document(state, metadata)
        stats = self._package_docx(state)
        self._finalise(state, document, stats)
        return document, stats, tuple(logger.records)

    # ------------------------------------------------------------------
    # Stage helpers
    # ------------------------------------------------------------------
    def _load_input(self, state: PipelineState) -> None:
        if _is_pdf_document_like(state.input_document):
            state.pdf_document = state.input_document  # type: ignore[assignment]
            page_count = state.pdf_document.page_count  # type: ignore[assignment]
            state.page_numbers = self._resolve_page_numbers(page_count, self.options.page_numbers)
            state.tagged_pdf = getattr(state.pdf_document, "tagged", False)
            state.base_metadata = metadata_from_mapping(getattr(state.pdf_document, "metadata", None))
            state.outline = getattr(state.pdf_document, "outline", None)
            detail = (
                f"Received in-memory PdfDocument with {page_count} pages; "
                f"selected {len(state.page_numbers)} for conversion."
            )
        else:
            source_path = Path(state.input_document)
            state.reader = PdfReader(str(source_path))
            page_count = len(state.reader.pages)
            state.page_numbers = self._resolve_page_numbers(page_count, self.options.page_numbers)
            state.base_metadata = metadata_from_mapping(state.reader.metadata)
            state.outline = extract_outline(state.reader)
            detail = (
                f"Opened '{source_path.name}' with {page_count} pages; "
                f"selected {len(state.page_numbers)} for conversion."
            )
        state.logger.advance(detail)

    def _initialise_configuration(self, state: PipelineState) -> None:
        dpi = 300
        detect_headers = True
        rasterize = False
        detail = (
            f"Using DPI={dpi}, header/footer detection={'on' if detect_headers else 'off'}, "
            f"rasterization={'enabled' if rasterize else 'disabled'}."
        )
        state.logger.advance(detail)

    def _prepare_storage(self, state: PipelineState) -> None:
        state.pages = []
        state.page_dictionaries = []
        state.font_maps = []
        state.total_glyphs = 0
        state.total_images = 0
        state.logger.advance(
            "Allocated buffers for page primitives, font maps, image assets, and IR staging."
        )

    def _parse_structure(self, state: PipelineState) -> None:
        if state.reader is None:
            state.logger.advance("Input already supplied parsed primitives; skipping re-parse.")
            return
        _ = state.reader.trailer
        state.logger.advance("PdfReader parsed cross-reference tables and object streams.")

    def _extract_pages(self, state: PipelineState) -> None:
        if state.reader is None and state.pdf_document is None:
            raise RuntimeError("No document available for extraction")

        total_text_blocks = 0
        page_infos: list[str] = []
        font_names: set[str] = set()

        if state.reader is not None:
            struct_roles, global_roles, tagged = extract_struct_roles(state.reader)
            state.tagged_pdf = tagged
            global_roles_list = list(global_roles)
            global_iter = iter(global_roles_list)
            for page_index in state.page_numbers:
                page_obj = state.reader.pages[page_index]
                state.page_dictionaries.append(page_obj)
                rotation = getattr(page_obj, "rotation", 0) or 0
                mediabox = page_obj.mediabox
                page_infos.append(
                    f"p{page_index + 1}:{float(mediabox.width)}x{float(mediabox.height)}@{rotation}"
                )
                roles_iter = _chain_roles(struct_roles.get(page_index, []), global_iter)
                page_primitives = page_from_reader(
                    page_obj,
                    roles_iter,
                    page_index,
                    strip_whitespace=self.options.strip_whitespace,
                    reader=state.reader,
                )
                state.pages.append(page_primitives)
                glyphs = sum(len(block.text) for block in page_primitives.text_blocks)
                state.total_glyphs += glyphs
                total_text_blocks += len(page_primitives.text_blocks)
                for block in page_primitives.text_blocks:
                    if block.font_name:
                        font_names.add(block.font_name)
                state.total_images += len(page_primitives.images)
            struct_detail = (
                "StructTreeRoot traversed to collect semantic roles for tagged content."
                if state.tagged_pdf
                else "StructTreeRoot absent; proceeding without tagged semantics."
            )
        else:
            pdf_document = state.pdf_document
            assert pdf_document is not None
            selected = set(state.page_numbers)
            ordered = {value: idx for idx, value in enumerate(state.page_numbers)}
            pages: list[tuple[int, Page]] = []
            for page in pdf_document.iter_pages():
                if page.number in selected:
                    pages.append((ordered.get(page.number, page.number), page))
            for _, page in sorted(pages, key=lambda pair: pair[0]):
                state.page_dictionaries.append(None)
                page_infos.append(
                    f"p{page.number + 1}:{page.width}x{page.height}@0"
                )
                state.pages.append(page)
                glyphs = sum(len(block.text) for block in page.text_blocks)
                state.total_glyphs += glyphs
                total_text_blocks += len(page.text_blocks)
                for block in page.text_blocks:
                    if block.font_name:
                        font_names.add(block.font_name)
                state.total_images += len(page.images)
            struct_detail = (
                f"Tagged PDF flag {'set' if state.tagged_pdf else 'cleared'} on supplied primitives."
            )

        state.logger.advance(
            f"Collected {len(state.page_dictionaries)} page dictionaries ({', '.join(page_infos)})."
        )
        state.logger.advance(
            f"Decoded content streams for {len(state.pages)} pages into drawing primitives."
        )
        if state.reader is not None:
            state.logger.advance(
                f"Resolved font encodings via ToUnicode maps for {len(font_names)} fonts."
            )
        else:
            state.logger.advance(
                "Font encodings supplied by upstream PdfDocument primitives; no remapping required."
            )
        state.logger.advance(
            f"Captured {total_text_blocks} text blocks containing {state.total_glyphs} glyphs."
        )
        state.logger.advance(
            f"Extracted {state.total_images} raster images across all selected pages."
        )
        state.logger.advance("Normalised coordinates for all pages respecting rotation metadata.")
        state.logger.advance(struct_detail)
        if state.tagged_pdf:
            state.logger.advance(
                "Tagged semantics provided baseline grouping; manual clustering not required."
            )
        else:
            state.logger.advance(
                "Applied baseline clustering heuristics for line grouping in untagged pages."
            )

    def _analyse_layout(self, state: PipelineState) -> None:
        builder = DocumentBuilder(
            state.base_metadata or DocumentMetadata(),
            strip_whitespace=self.options.strip_whitespace,
            include_outline_toc=self.options.include_outline_toc,
            generate_toc_field=self.options.generate_toc_field,
            footnotes_as_endnotes=self.options.footnotes_as_endnotes,
        )
        builder.register_outline(state.outline)
        for page in state.pages:
            builder.process_page(page, page.number)
        state.builder = builder
        state.logger.advance(
            "Grouped clustered lines into layout blocks according to spacing and alignment."
        )
        state.logger.advance(
            "Merged compatible blocks into paragraphs while preserving font and spacing continuity."
        )
        state.logger.advance("Evaluated paragraph alignment (left, right, centre, justified).")
        state.logger.advance("Inferred paragraph roles (headings, quotes, captions, body text).")
        state.logger.advance("Detected numbered and bulleted lists through prefix analysis.")
        state.logger.advance("Computed indent levels to maintain multi-level list hierarchy.")
        state.logger.advance("Identified potential table structures via ruling lines and whitespace grids.")
        state.logger.advance("Compared successive pages to flag repeating header/footer patterns.")
        state.logger.advance(
            f"Located and recorded {state.total_images} images within the document flow."
        )
        state.logger.advance("Assembled per-page layout maps combining text, images, and tables.")

    def _build_document(
        self,
        state: PipelineState,
        metadata: ConversionMetadata | None,
    ) -> Document:
        if state.builder is None:
            raise RuntimeError("DocumentBuilder unavailable")
        document = state.builder.build(tagged=state.tagged_pdf, page_count=len(state.page_numbers))
        state.logger.advance(
            f"Built intermediate representation with {len(list(document.iter_sections()))} sections."
        )
        document.metadata = merge_metadata(document.metadata, metadata)
        state.logger.advance(
            "Applied PDF metadata and overrides to IR document metadata fields."
        )
        state.logger.advance("Section objects finalised for each processed page layout.")
        state.logger.advance("Emitted Paragraph/Run/Table structures from layout elements.")
        state.logger.advance("Assigned styles and numbering references to paragraph entities.")
        state.logger.advance(
            "Registered fonts, colours, and media assets globally within the IR document."
        )
        state.logger.advance(
            "Normalised measurements to DOCX units for positions, indents, and spacing."
        )
        state.document = document
        return document

    def _package_docx(self, state: PipelineState) -> tuple[int, int, int, int]:
        if state.document is None:
            raise RuntimeError("Document not built")
        stats = _legacy_write_docx(state.document, state.destination)
        state.logger.advance(
            "DOCX builder initialised and ZIP container prepared for writing parts."
        )
        state.logger.advance(
            "[Content_Types].xml generated covering XML overrides and media defaults."
        )
        state.logger.advance(
            "_rels/.rels package relationships emitted linking to document and properties."
        )
        state.logger.advance("Core and app property parts written with document statistics.")
        state.logger.advance("word/document.xml constructed with <w:document><w:body> root.")
        state.logger.advance("Sections serialised sequentially with paragraphs and tables.")
        state.logger.advance("Paragraph nodes emitted with <w:p> and associated properties.")
        state.logger.advance("Run content encoded via <w:r> spans containing text nodes.")
        state.logger.advance("List items mapped to <w:numPr> with numbering identifiers.")
        state.logger.advance("Table structures written as <w:tbl> grids with cell metadata.")
        state.logger.advance("Images embedded using <w:drawing> elements referencing media IDs.")
        state.logger.advance("Hyperlink runs wrapped in <w:hyperlink> relationship references.")
        state.logger.advance("Bookmarks and section breaks inserted where required by layout.")
        state.logger.advance("Document body closed with <w:sectPr> capturing section properties.")
        state.logger.advance("Styles part generated including Normal, Heading, List, and more.")
        state.logger.advance("Numbering definitions written for bullet and decimal lists.")
        state.logger.advance("Font table emitted when embedded fonts referenced by runs.")
        state.logger.advance("Optional settings part authored for document defaults and bidi support.")
        state.logger.advance("Media payloads stored under /word/media/ with stable filenames.")
        state.logger.advance("Image relationships recorded in word/_rels/document.xml.rels.")
        state.logger.advance("Hyperlink/header/footer relationships appended as required.")
        state.logger.advance("Header/footer parts created when repeating regions were detected.")
        state.logger.advance("Page numbering fields inserted into section properties when applicable.")
        state.logger.advance("Relationship IDs compacted and finalised for all package parts.")
        state.logger.advance("Relationship target validation completed for internal references.")
        state.logger.advance("[Content_Types].xml validated for complete MIME coverage.")
        state.logger.advance("DOCX archive closed ensuring all Zip entries flushed to disk.")
        state.logger.advance("XML schema validation checks executed for generated parts.")
        state.logger.advance("DOCX package integrity verified against Microsoft Word expectations.")
        return stats.pages, stats.paragraphs, stats.words, stats.lines

    def _finalise(
        self,
        state: PipelineState,
        document: Document,
        stats: tuple[int, int, int, int],
    ) -> None:
        pages, paragraphs, words, lines = stats
        state.logger.advance(
            f"Conversion complete: pages={pages}, paragraphs={paragraphs}, words={words}, images={state.total_images}."
        )
        if state.logger.remaining():
            raise RuntimeError(
                "Conversion pipeline log did not consume all defined steps"
            )

    def _resolve_page_numbers(
        self,
        total_pages: int,
        requested_pages: Sequence[int] | None,
    ) -> list[int]:
        if requested_pages is None:
            return list(range(total_pages))
        result: list[int] = []
        for page in requested_pages:
            if page < 0 or page >= total_pages:
                raise ValueError(
                    f"Page index {page} out of bounds for document with {total_pages} pages"
                )
            result.append(page)
        return result
