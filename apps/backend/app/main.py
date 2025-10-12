"""FastAPI application exposing PDF utilities from the shared library."""

from __future__ import annotations

import json
from datetime import datetime
from json import JSONDecodeError
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable, List, Sequence
from zipfile import ZipFile

from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.concurrency import run_in_threadpool
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from intellipdf import (
    ConversionMetadata,
    ConversionOptions,
    extract_pages,
    get_split_info,
    merge_pdfs,
    split_pdf,
)
from intellipdf.pdf2docx.converter import PdfToDocxConverter
from intellipdf.split.exceptions import IntelliPDFSplitError, InvalidPageRangeError
from intellipdf.split.utils import PageRange, parse_page_ranges

app = FastAPI(title="IntelliPDF API", version="0.2.0")
DOCS_PREFIX = "/api"

def _cleanup_temp_dir(background_tasks: BackgroundTasks, temp_dir: TemporaryDirectory) -> None:
    """Schedule ``temp_dir`` to be cleaned up after the response is sent."""

    background_tasks.add_task(temp_dir.cleanup)


async def _store_upload(upload: UploadFile, destination: Path) -> Path:
    """Persist an uploaded file to ``destination`` and return the resulting path."""

    contents = await upload.read()
    if not contents:
        raise HTTPException(status_code=400, detail=f"File '{upload.filename}' is empty.")

    destination.write_bytes(contents)
    return destination


def _zip_outputs(files: Iterable[Path], destination: Path) -> Path:
    """Create a zip archive containing ``files`` at ``destination``."""

    with ZipFile(destination, "w") as archive:
        for file_path in files:
            archive.write(file_path, arcname=file_path.name)
    return destination


def _flatten_ranges(ranges: Sequence[PageRange]) -> list[int]:
    """Expand :class:`PageRange` values into a list of 1-indexed page numbers."""

    pages: list[int] = []
    for page_range in ranges:
        pages.extend(range(page_range.start, page_range.end + 1))
    return pages


def _safe_filename(filename: str | None, default: str) -> str:
    """Return a filesystem-safe filename derived from user input."""

    if not filename:
        return default

    candidate = Path(filename).name
    return candidate or default


def _parse_json_mapping(raw_value: str | None, *, field_name: str) -> dict[str, object] | None:
    """Parse an optional JSON encoded mapping from a multipart form field."""

    if raw_value is None:
        return None

    try:
        payload = json.loads(raw_value)
    except JSONDecodeError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=400, detail=f"{field_name} must be valid JSON.") from exc

    if payload is None:
        return None

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail=f"{field_name} must be a JSON object.")

    return payload


def _parse_page_numbers(value: object) -> list[int]:
    """Normalise page number selections to zero-based indices."""

    raw_items: list[object]
    if isinstance(value, str):
        raw_items = [item.strip() for item in value.split(",") if item.strip()]
    elif isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, str)):
        raw_items = list(value)
    else:
        raise HTTPException(status_code=400, detail="'page_numbers' must be a list of integers.")

    if not raw_items:
        raise HTTPException(status_code=400, detail="'page_numbers' must contain at least one entry.")

    try:
        parsed = [int(item) for item in raw_items]
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="'page_numbers' must be integers.") from exc

    if all(number >= 1 for number in parsed) and 0 not in parsed:
        parsed = [number - 1 for number in parsed]

    if any(number < 0 for number in parsed):
        raise HTTPException(status_code=400, detail="'page_numbers' must be positive integers.")

    return parsed


def _extract_page_selection(payload: dict[str, object] | None) -> list[int] | None:
    """Extract an optional list of page numbers from ``payload``."""

    if not payload:
        return None

    page_numbers = payload.get("page_numbers") or payload.get("pageNumbers")
    if page_numbers is None:
        return None

    return _parse_page_numbers(page_numbers)


def _parse_datetime(value: object, *, field: str) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:  # pragma: no cover - defensive
            raise HTTPException(status_code=400, detail=f"'{field}' must be an ISO formatted datetime.") from exc
    raise HTTPException(status_code=400, detail=f"'{field}' must be an ISO formatted datetime string.")


def _build_conversion_metadata(payload: dict[str, object] | None) -> ConversionMetadata | None:
    if not payload:
        return None

    metadata = ConversionMetadata()
    updated = False

    simple_fields = {
        "title": "title",
        "author": "author",
        "subject": "subject",
        "description": "description",
        "language": "language",
        "revision": "revision",
        "last_modified_by": "lastModifiedBy",
    }

    for canonical, alias in simple_fields.items():
        raw_value = payload.get(canonical)
        if raw_value is None:
            raw_value = payload.get(alias)
        if raw_value is None:
            continue
        setattr(metadata, canonical, str(raw_value))
        updated = True

    for field_name, alias in {"created": "created", "modified": "modified"}.items():
        raw_value = payload.get(field_name)
        if raw_value is None:
            raw_value = payload.get(alias)
        if raw_value is None:
            continue
        setattr(metadata, field_name, _parse_datetime(raw_value, field=field_name))
        updated = True

    keywords = payload.get("keywords")
    if keywords is None:
        keywords = payload.get("keywordList")
    if keywords is not None:
        if isinstance(keywords, str):
            parts = [part.strip() for part in keywords.split(",") if part.strip()]
        elif isinstance(keywords, Iterable) and not isinstance(keywords, (bytes, bytearray)):
            parts = [str(part).strip() for part in keywords if str(part).strip()]
        else:
            raise HTTPException(status_code=400, detail="'keywords' must be a list of strings or comma separated string.")
        metadata.keywords = parts or None
        updated = updated or bool(parts)

    return metadata if updated else None


@app.get("/health", response_class=JSONResponse)
async def health() -> dict[str, str]:
    """Lightweight health endpoint for uptime checks."""
    return {"status": "ok"}


@app.get(
    f"{DOCS_PREFIX}/openapi.json",
    include_in_schema=False,
    name="prefixed_openapi",
)
async def prefixed_openapi() -> JSONResponse:
    """Expose the OpenAPI schema under the gateway's ``/api`` prefix."""

    return JSONResponse(app.openapi())


@app.get(f"{DOCS_PREFIX}/docs", include_in_schema=False)
async def prefixed_swagger_ui(request: Request) -> HTMLResponse:
    """Serve Swagger UI from the same ``/api`` prefix used by the gateway."""

    return get_swagger_ui_html(
        openapi_url=str(request.url_for("prefixed_openapi")),
        title=f"{app.title} - Swagger UI",
    )


@app.post("/merge", response_class=FileResponse)
async def merge_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(..., description="PDF files to merge"),
    document_info: str | None = Form(
        None,
        description="Optional JSON encoded metadata to apply to the merged PDF.",
    ),
    add_bookmarks: bool = Form(
        False,
        description="When true, create bookmarks for each merged document.",
    ),
) -> FileResponse:
    """Merge multiple PDF uploads into a single document.

    The endpoint stores incoming files on disk, delegates merging to the
    shared :mod:`intellipdf` library, then returns the merged PDF. All
    temporary files are cleaned up once the response is sent.
    """

    if not files:
        raise HTTPException(status_code=400, detail="At least one PDF must be provided.")

    temp_dir = TemporaryDirectory()
    temp_path = Path(temp_dir.name)
    stored_files: list[Path] = []

    for index, upload in enumerate(files, start=1):
        contents = await upload.read()
        if not contents:
            raise HTTPException(status_code=400, detail=f"File '{upload.filename}' is empty.")

        filename = _safe_filename(upload.filename, f"document_{index}.pdf")
        file_path = temp_path / filename
        file_path.write_bytes(contents)
        stored_files.append(file_path)

    output_path = temp_path / "merged.pdf"

    metadata_overrides: dict[str, object] | None = None
    if document_info:
        try:
            parsed_info = json.loads(document_info)
        except JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="document_info must be valid JSON.") from exc

        if not isinstance(parsed_info, dict):
            raise HTTPException(status_code=400, detail="document_info must be a JSON object.")

        metadata_overrides = {
            str(key): value
            for key, value in parsed_info.items()
            if value is not None
        }

    bookmark_titles: list[str] | None = None
    if add_bookmarks:
        bookmark_titles = [path.stem or f"Document {index}" for index, path in enumerate(stored_files, start=1)]

    try:
        merge_pdfs(
            stored_files,
            output_path,
            document_info=metadata_overrides,
            bookmarks=bookmark_titles,
        )
    except Exception as exc:  # pragma: no cover - defensive conversion to HTTP error
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    _cleanup_temp_dir(background_tasks, temp_dir)

    return FileResponse(
        output_path,
        media_type="application/pdf",
        filename="merged.pdf",
    )


@app.post(
    "/split/ranges",
    response_class=FileResponse,
    summary="Extract specific page ranges",
    response_description="PDF file containing the requested page ranges.",
)
async def extract_page_ranges(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Source PDF to extract ranges from."),
    ranges: str = Form(..., description="Comma separated page ranges, e.g. '1-3,7-9'."),
) -> FileResponse:
    """Extract the provided page ranges into a single PDF document."""

    temp_dir = TemporaryDirectory()
    temp_path = Path(temp_dir.name)
    input_path = temp_path / _safe_filename(file.filename, "document.pdf")
    await _store_upload(file, input_path)

    try:
        info = get_split_info(input_path)
        parsed_ranges = parse_page_ranges(ranges, total_pages=info["pages"])
    except InvalidPageRangeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntelliPDFSplitError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive conversion to HTTP error
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    output_path = temp_path / "extracted.pdf"

    try:
        extract_pages(input_path, _flatten_ranges(parsed_ranges), output_path)
    except IntelliPDFSplitError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive conversion to HTTP error
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    _cleanup_temp_dir(background_tasks, temp_dir)

    return FileResponse(
        output_path,
        media_type="application/pdf",
        filename="extracted_ranges.pdf",
    )


@app.post(
    "/split/pages",
    response_class=FileResponse,
    summary="Split a PDF at specific pages",
    response_description="Zip archive containing PDF segments.",
)
async def split_at_pages(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Source PDF to split."),
    pages: str = Form(..., description="Comma separated page numbers where a new split should start."),
) -> FileResponse:
    """Split a PDF into segments using explicit split points."""

    temp_dir = TemporaryDirectory()
    temp_path = Path(temp_dir.name)
    input_path = temp_path / _safe_filename(file.filename, "document.pdf")
    await _store_upload(file, input_path)

    try:
        info = get_split_info(input_path)
        total_pages = int(info["pages"])
    except Exception as exc:  # pragma: no cover - defensive conversion to HTTP error
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    try:
        split_points = sorted({int(point.strip()) for point in pages.split(",") if point.strip()})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Split points must be integers.") from exc

    if not split_points:
        raise HTTPException(status_code=400, detail="At least one split point must be provided.")

    if any(point <= 1 or point > total_pages for point in split_points):
        raise HTTPException(
            status_code=400,
            detail="Split points must be between 2 and the total number of pages.",
        )

    segments: list[tuple[int, int]] = []
    start_page = 1
    for point in split_points:
        if point <= start_page:
            raise HTTPException(status_code=400, detail="Split points must be in ascending order.")
        segments.append((start_page, point - 1))
        start_page = point
    if start_page <= total_pages:
        segments.append((start_page, total_pages))

    output_dir = temp_path / "parts"

    try:
        generated = split_pdf(input_path, output_dir, mode="range", ranges=segments)
    except IntelliPDFSplitError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive conversion to HTTP error
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    archive_path = _zip_outputs(generated, temp_path / "split_pages.zip")

    _cleanup_temp_dir(background_tasks, temp_dir)

    return FileResponse(
        archive_path,
        media_type="application/zip",
        filename="split_pages.zip",
    )


@app.post(
    "/split/every-n",
    response_class=FileResponse,
    summary="Split a PDF every N pages",
    response_description="Zip archive containing PDF segments.",
)
async def split_every_n(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Source PDF to split."),
    chunk_size: int = Form(..., ge=1, description="Number of pages per split."),
) -> FileResponse:
    """Split a PDF into equal-sized segments of ``chunk_size`` pages."""

    if chunk_size < 1:
        raise HTTPException(status_code=400, detail="Chunk size must be at least 1.")

    temp_dir = TemporaryDirectory()
    temp_path = Path(temp_dir.name)
    input_path = temp_path / _safe_filename(file.filename, "document.pdf")
    await _store_upload(file, input_path)

    try:
        info = get_split_info(input_path)
        total_pages = int(info["pages"])
    except Exception as exc:  # pragma: no cover - defensive conversion to HTTP error
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    ranges_to_split: list[tuple[int, int]] = []
    start = 1
    while start <= total_pages:
        end = min(start + chunk_size - 1, total_pages)
        ranges_to_split.append((start, end))
        start = end + 1

    output_dir = temp_path / "chunks"

    try:
        generated = split_pdf(input_path, output_dir, mode="range", ranges=ranges_to_split)
    except IntelliPDFSplitError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive conversion to HTTP error
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    archive_path = _zip_outputs(generated, temp_path / "split_every_n.zip")

    _cleanup_temp_dir(background_tasks, temp_dir)

    return FileResponse(
        archive_path,
        media_type="application/zip",
        filename=f"split_every_{chunk_size}.zip",
    )


@app.post(
    "/split/all-pages",
    response_class=FileResponse,
    summary="Extract every page into individual PDFs",
    response_description="Zip archive containing a PDF per page.",
)
async def extract_all_pages(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Source PDF to split into individual pages."),
) -> FileResponse:
    """Extract each page in ``file`` into its own PDF document."""

    temp_dir = TemporaryDirectory()
    temp_path = Path(temp_dir.name)
    input_path = temp_path / _safe_filename(file.filename, "document.pdf")
    await _store_upload(file, input_path)

    try:
        info = get_split_info(input_path)
        total_pages = int(info["pages"])
    except Exception as exc:  # pragma: no cover - defensive conversion to HTTP error
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    output_dir = temp_path / "pages"

    try:
        generated = split_pdf(
            input_path,
            output_dir,
            mode="pages",
            pages=list(range(1, total_pages + 1)),
        )
    except IntelliPDFSplitError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive conversion to HTTP error
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    archive_path = _zip_outputs(generated, temp_path / "all_pages.zip")

    _cleanup_temp_dir(background_tasks, temp_dir)

    return FileResponse(
        archive_path,
        media_type="application/zip",
        filename="all_pages.zip",
    )


@app.post(
    "/convert/pdf-to-docx",
    response_class=FileResponse,
    summary="Convert a PDF document to DOCX",
    response_description="DOCX document converted from the uploaded PDF.",
)
async def convert_pdf_to_docx_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Source PDF to convert."),
    options: str | None = Form(
        None,
        description="Optional JSON object controlling conversion behaviour.",
    ),
    metadata: str | None = Form(
        None,
        description="Optional JSON object providing DOCX metadata overrides.",
    ),
) -> FileResponse:
    """Convert an uploaded PDF into a DOCX document."""

    temp_dir = TemporaryDirectory()
    temp_path = Path(temp_dir.name)
    input_path = temp_path / _safe_filename(file.filename, "document.pdf")
    await _store_upload(file, input_path)

    page_numbers = _extract_page_selection(_parse_json_mapping(options, field_name="options"))
    conversion_metadata = _build_conversion_metadata(
        _parse_json_mapping(metadata, field_name="metadata")
    )

    output_filename = input_path.with_suffix(".docx").name
    output_path = temp_path / output_filename

    try:
        result = await run_in_threadpool(
            _perform_pdf_to_docx_conversion,
            input_path,
            output_path,
            page_numbers,
            conversion_metadata,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive conversion to HTTP error
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    _cleanup_temp_dir(background_tasks, temp_dir)

    headers = {
        "X-IntelliPDF-Docx-Page-Count": str(result.page_count),
        "X-IntelliPDF-Docx-Paragraph-Count": str(result.paragraph_count),
        "X-IntelliPDF-Docx-Word-Count": str(result.word_count),
        "X-IntelliPDF-Docx-Line-Count": str(result.line_count),
    }

    return FileResponse(
        result.output_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=output_filename,
        headers=headers,
    )


__all__ = ["app"]


def _perform_pdf_to_docx_conversion(
    input_path: Path,
    output_path: Path,
    page_numbers: list[int] | None,
    conversion_metadata: ConversionMetadata | None,
):
    """Convert ``input_path`` PDF to DOCX by delegating to the pdf2docx package.

    The backend's job is to configure :class:`ConversionOptions` and hand control to
    :class:`PdfToDocxConverter`. The converter is responsible for the detailed pipeline
    (opening the PDF, parsing structure, extracting fonts/images, building the
    intermediate representation, generating DOCX parts, and validating the package).
    """

    options = ConversionOptions(
        page_numbers=page_numbers,
        strip_whitespace=False,
        stream_pages=False,
        include_outline_toc=False,
        generate_toc_field=False,
        footnotes_as_endnotes=False,
    )

    converter = PdfToDocxConverter(options)
    return converter.convert(
        input_path,
        output_path,
        metadata=conversion_metadata,
    )
