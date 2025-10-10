"""FastAPI application exposing PDF utilities from the shared library."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from intellipdf import merge_pdfs

app = FastAPI(title="IntelliPDF API", version="0.1.0")


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

    background_tasks.add_task(temp_dir.cleanup)

    return FileResponse(
        output_path,
        media_type="application/pdf",
        filename="merged.pdf",
    )


__all__ = ["app"]
