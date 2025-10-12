"""FastAPI application exposing PDF utilities from the shared library."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable, List, Sequence
from zipfile import ZipFile

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from intellipdf import extract_pages, get_split_info, merge_pdfs, split_pdf
from intellipdf.split.exceptions import IntelliPDFSplitError, InvalidPageRangeError
from intellipdf.split.utils import PageRange, parse_page_ranges

app = FastAPI(title="IntelliPDF API", version="0.2.0")


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


@app.get("/health", response_class=JSONResponse)
async def health() -> dict[str, str]:
    """Lightweight health endpoint for uptime checks."""
    return {"status": "ok"}


@app.post("/merge", response_class=FileResponse)
async def merge_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(..., description="PDF files to merge"),
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

        filename = upload.filename or f"document_{index}.pdf"
        file_path = temp_path / filename
        file_path.write_bytes(contents)
        stored_files.append(file_path)

    output_path = temp_path / "merged.pdf"

    try:
        merge_pdfs(stored_files, output_path)
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
    input_path = temp_path / (file.filename or "document.pdf")
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
    input_path = temp_path / (file.filename or "document.pdf")
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
    input_path = temp_path / (file.filename or "document.pdf")
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
    input_path = temp_path / (file.filename or "document.pdf")
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


__all__ = ["app"]
