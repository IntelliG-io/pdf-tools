"""PDF splitting functionality built around :class:`PDFDocumentAdapter`."""

from __future__ import annotations

import math
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union

from .document import PDFDocumentAdapter
from .backends.base import PDFBackend
from .exceptions import (
    EncryptedPDFError,
    InvalidPDFError,
    InvalidRangeError,
    InsufficientDiskSpaceError,
    PageOutOfBoundsError,
    PDFSplitterException,
)
from .manifest import BatchManifest
from .types import BatchResult, SplitResult

RangeList = List[Tuple[int, int]]
PageList = List[int]


def parse_ranges(ranges_str: str) -> RangeList:
    """Parse a comma-separated range string into (start, end) tuples."""

    if not ranges_str or not ranges_str.strip():
        raise InvalidRangeError("Ranges string cannot be empty")

    ranges: RangeList = []
    for token in ranges_str.split(","):
        token = token.strip()
        match = re.match(r"^(\d+)-(\d+)$", token)
        if not match:
            raise InvalidRangeError(
                f"Invalid range format: '{token}'. Expected 'start-end'."
            )

        start = int(match.group(1))
        end = int(match.group(2))
        if start > end:
            raise InvalidRangeError(
                f"Invalid range '{token}': start page ({start}) must be <= end page ({end})."
            )
        if start < 1:
            raise PageOutOfBoundsError(
                f"Invalid range '{token}': page numbers must be >= 1."
            )

        ranges.append((start, end))

    return ranges


def parse_page_spec(page_spec: str) -> PageList:
    """Parse a page specification string into sorted unique page numbers."""

    if not page_spec or not page_spec.strip():
        raise InvalidRangeError("Page specification cannot be empty")

    pages: set[int] = set()
    for token in page_spec.split(","):
        token = token.strip()
        if "-" in token:
            match = re.match(r"^(\d+)-(\d+)$", token)
            if not match:
                raise InvalidRangeError(
                    f"Invalid page range format: '{token}'. Expected 'start-end'."
                )

            start = int(match.group(1))
            end = int(match.group(2))
            if start > end:
                raise InvalidRangeError(
                    f"Invalid range '{token}': start page ({start}) must be <= end page ({end})."
                )
            if start < 1:
                raise PageOutOfBoundsError(
                    f"Invalid range '{token}': page numbers must be >= 1."
                )

            pages.update(range(start, end + 1))
        else:
            if not token.isdigit():
                raise InvalidRangeError(
                    f"Invalid page number: '{token}'. Expected a positive integer."
                )

            page_num = int(token)
            if page_num < 1:
                raise PageOutOfBoundsError(
                    f"Invalid page number: {page_num}. Page numbers must be >= 1."
                )

            pages.add(page_num)

    return sorted(pages)


def validate_ranges(
    ranges: RangeList,
    total_pages: int,
    check_overlaps: bool = True,
) -> None:
    """Validate ranges against PDF bounds and overlaps."""

    if not ranges:
        raise InvalidRangeError("No ranges provided")

    for start, end in ranges:
        if start < 1 or end < 1:
            raise PageOutOfBoundsError("Range values must be >= 1")
        if end > total_pages:
            raise PageOutOfBoundsError(
                f"Range {start}-{end} exceeds PDF page count ({total_pages} pages)."
            )
        if start > end:
            raise InvalidRangeError(
                f"Range {start}-{end} is invalid because start > end."
            )

    if check_overlaps and len(ranges) > 1:
        sorted_ranges = sorted(ranges)
        for current, nxt in zip(sorted_ranges, sorted_ranges[1:]):
            if current[1] >= nxt[0]:
                raise InvalidRangeError(
                    f"Overlapping ranges detected: {current[0]}-{current[1]} and {nxt[0]}-{nxt[1]}."
                )


class PDFSplitter:
    """High-level PDF splitting operations."""

    def __init__(
        self,
        input_path: str,
        *,
        password: Optional[str] = None,
        backend: Optional[PDFBackend] = None,
    ) -> None:
        self.input_path = input_path
        self._adapter = PDFDocumentAdapter(input_path, password=password, backend=backend)
        self.num_pages = self._adapter.num_pages

    @staticmethod
    def _ensure_output_dir(output_dir: str, required_mb: int = 10) -> Path:
        return PDFDocumentAdapter.ensure_directory_writable(
            output_dir, required_mb=required_mb
        )

    def _write_pdf(self, writer: Any, destination: Path) -> None:
        try:
            self._adapter.write(writer, destination)
        except InsufficientDiskSpaceError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            raise PDFSplitterException(
                f"Unexpected error writing file: {destination}. Error: {exc}"
            ) from exc

    def split_to_pages(
        self,
        output_dir: str,
        prefix: str = "page",
        padding: int = 3,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[str]:
        output_path = self._ensure_output_dir(output_dir)

        created_files: List[str] = []
        for index in range(self.num_pages):
            writer = self._adapter.new_writer()
            writer.add_page(self._adapter.get_page(index))
            self._adapter.copy_metadata(
                writer,
                title_suffix=f" - Page {index + 1}",
                pages_label=f"Page {index + 1}",
            )

            filename = f"{prefix}_{(index + 1):0{padding}d}.pdf"
            destination = output_path / filename
            self._write_pdf(writer, destination)
            created_files.append(str(destination))

            if progress_callback:
                progress_callback(index + 1, self.num_pages)

        return created_files

    def split_by_range(
        self,
        output_dir: str,
        start_page: int,
        end_page: int,
        output_filename: Optional[str] = None,
    ) -> str:
        if start_page < 1 or end_page > self.num_pages:
            raise PageOutOfBoundsError(
                f"Invalid page range: {start_page}-{end_page}. PDF has {self.num_pages} pages."
            )
        if start_page > end_page:
            raise InvalidRangeError(
                f"Start page ({start_page}) must be <= end page ({end_page})"
            )

        output_path = self._ensure_output_dir(output_dir)
        filename = output_filename or f"pages_{start_page}-{end_page}.pdf"
        destination = output_path / filename

        writer = self._adapter.new_writer()
        for page_num in range(start_page - 1, end_page):
            writer.add_page(self._adapter.get_page(page_num))

        self._adapter.copy_metadata(
            writer,
            title_suffix=f" - Pages {start_page}-{end_page}",
            pages_label=f"Pages {start_page}-{end_page}",
        )
        self._write_pdf(writer, destination)
        return str(destination)

    def split_by_ranges(
        self,
        ranges: Union[str, RangeList],
        output_dir: str,
        prefix: str = "range",
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[str]:
        parsed_ranges = parse_ranges(ranges) if isinstance(ranges, str) else ranges
        validate_ranges(parsed_ranges, self.num_pages, check_overlaps=True)

        output_path = self._ensure_output_dir(output_dir)
        created_files: List[str] = []

        for index, (start_page, end_page) in enumerate(parsed_ranges, start=1):
            writer = self._adapter.new_writer()
            for page_num in range(start_page - 1, end_page):
                writer.add_page(self._adapter.get_page(page_num))

            self._adapter.copy_metadata(
                writer,
                title_suffix=f" - Pages {start_page}-{end_page}",
                pages_label=f"Pages {start_page}-{end_page}",
            )

            destination = output_path / f"{prefix}_{start_page}-{end_page}.pdf"
            self._write_pdf(writer, destination)
            created_files.append(str(destination))

            if progress_callback:
                progress_callback(index, len(parsed_ranges))

        return created_files

    def split_by_chunks(
        self,
        chunk_size: int,
        output_dir: str,
        prefix: str = "chunk",
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[str]:
        if chunk_size < 1:
            raise InvalidRangeError(f"Chunk size must be >= 1, got {chunk_size}")
        if chunk_size > self.num_pages:
            raise InvalidRangeError(
                f"Chunk size ({chunk_size}) cannot exceed total pages ({self.num_pages})"
            )

        output_path = self._ensure_output_dir(output_dir)
        created_files: List[str] = []

        num_chunks = math.ceil(self.num_pages / chunk_size)
        for chunk_index in range(num_chunks):
            start_page = chunk_index * chunk_size
            end_page = min(start_page + chunk_size, self.num_pages)

            writer = self._adapter.new_writer()
            for page_num in range(start_page, end_page):
                writer.add_page(self._adapter.get_page(page_num))

            self._adapter.copy_metadata(
                writer,
                title_suffix=f" - Pages {start_page + 1}-{end_page}",
                pages_label=f"Pages {start_page + 1}-{end_page}",
            )

            destination = output_path / f"{prefix}_{(chunk_index + 1):03d}.pdf"
            self._write_pdf(writer, destination)
            created_files.append(str(destination))

            if progress_callback:
                progress_callback(chunk_index + 1, num_chunks)

        return created_files

    def extract_pages(
        self,
        pages: Union[str, Iterable[int]],
        output_path: str,
    ) -> str:
        page_list = (
            parse_page_spec(pages) if isinstance(pages, str) else sorted(set(pages))
        )
        for page_num in page_list:
            if page_num < 1 or page_num > self.num_pages:
                raise PageOutOfBoundsError(
                    f"Page {page_num} is out of bounds. PDF has {self.num_pages} pages."
                )

        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)

        writer = self._adapter.new_writer()
        for page_num in page_list:
            writer.add_page(self._adapter.get_page(page_num - 1))

        if len(page_list) == 1:
            suffix = f" - Page {page_list[0]}"
            label = f"Page {page_list[0]}"
        else:
            if len(page_list) <= 5:
                pages_str = ",".join(map(str, page_list))
            else:
                pages_str = f"{page_list[0]}-{page_list[-1]}"
            suffix = f" - Pages {pages_str}"
            label = f"Pages {pages_str}"

        self._adapter.copy_metadata(writer, title_suffix=suffix, pages_label=label)
        self._write_pdf(writer, destination)
        return str(destination)

    def get_page_count(self) -> int:
        return self.num_pages

    def split_to_pages_with_result(
        self,
        output_dir: str,
        prefix: str = "page",
        padding: int = 3,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> SplitResult:
        files = self.split_to_pages(
            output_dir=output_dir,
            prefix=prefix,
            padding=padding,
            progress_callback=progress_callback,
        )
        return SplitResult(
            success=True,
            files_created=files,
            total_files=len(files),
            source_file=self.input_path,
            operation="split-pages",
        )


class BatchProcessor:
    """Handle batch processing of multiple PDF files."""

    def __init__(
        self,
        *,
        passwords: Optional[Dict[str, str]] = None,
        backend: Optional[PDFBackend] = None,
        max_retries: int = 1,
        manifest_path: Optional[str] = None,
        resume: bool = True,
        required_mb: int = 10,
        retry_backoff_seconds: float = 0.0,
    ) -> None:
        self.passwords = passwords or {}
        self.backend = backend
        self.max_retries = max(0, max_retries)
        self.manifest_path = Path(manifest_path) if manifest_path else None
        self.resume = resume
        self.required_mb = max(0, required_mb)
        self.retry_backoff_seconds = max(0.0, retry_backoff_seconds)

    def _create_splitter(self, pdf_file: str) -> PDFSplitter:
        password = self._password_for(pdf_file)
        return PDFSplitter(pdf_file, password=password, backend=self.backend)

    def find_pdf_files(self, input_dir: str) -> List[str]:
        input_path = Path(input_dir)
        if not input_path.exists():
            raise FileNotFoundError(f"Directory not found: {input_dir}")
        if not input_path.is_dir():
            raise InvalidPDFError(f"Not a directory: {input_dir}")

        return sorted(str(path) for path in input_path.glob("*.pdf") if path.is_file())

    def _password_for(self, pdf_path: str) -> Optional[str]:
        return self.passwords.get(Path(pdf_path).name)

    def process_directory(
        self,
        input_dir: str,
        operation: str,
        output_dir: str,
        options: Optional[Dict[str, Union[str, int, List[Tuple[int, int]], Iterable[int]]]] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> BatchResult:
        options = options or {}
        pdf_files = self.find_pdf_files(input_dir)

        base_output = Path(output_dir)
        base_output.mkdir(parents=True, exist_ok=True)

        manifest_path = self.manifest_path or (base_output / "batch-manifest.json")
        manifest = BatchManifest.load(manifest_path)

        if not pdf_files:
            manifest.save()
            return BatchResult(
                total=0,
                success=0,
                failure=0,
                skipped=0,
                results=[],
                manifest_path=str(manifest_path),
                total_attempts=0,
            )

        results: List[Dict[str, Union[str, int, List[str]]]] = []
        skipped_count = 0
        success_count = 0
        failure_count = 0

        for index, pdf_file in enumerate(pdf_files, start=1):
            if progress_callback:
                progress_callback(Path(pdf_file).name, index, len(pdf_files))

            if self.resume and manifest.should_skip(pdf_file):
                entry = manifest.get(pdf_file)
                results.append(
                    {
                        "file": pdf_file,
                        "status": "skipped",
                        "files_created": entry.files_created,
                        "attempts": entry.attempts,
                        "output_dir": str(base_output / Path(pdf_file).stem),
                    }
                )
                skipped_count += 1
                continue

            pdf_output_dir = base_output / Path(pdf_file).stem
            PDFDocumentAdapter.ensure_directory_writable(
                str(pdf_output_dir), required_mb=self.required_mb
            )

            attempt_error: Optional[str] = None
            while True:
                entry = manifest.increment_attempt(pdf_file)
                manifest.save()

                try:
                    splitter = self._create_splitter(pdf_file)

                    created: List[str]
                    if operation == "pages":
                        created = splitter.split_to_pages(
                            output_dir=str(pdf_output_dir),
                            prefix=str(options.get("prefix", "page")),
                            padding=int(options.get("padding", 3)),
                        )
                    elif operation == "chunks":
                        chunk_size = int(options.get("chunk_size", 10))
                        created = splitter.split_by_chunks(
                            chunk_size=chunk_size,
                            output_dir=str(pdf_output_dir),
                            prefix=str(options.get("prefix", "chunk")),
                        )
                    elif operation == "ranges":
                        ranges_option = options.get("ranges")
                        if ranges_option is None:
                            raise InvalidRangeError("Ranges option is required for 'ranges' operation")
                        created = splitter.split_by_ranges(
                            ranges=ranges_option,  # type: ignore[arg-type]
                            output_dir=str(pdf_output_dir),
                            prefix=str(options.get("prefix", "range")),
                        )
                    elif operation == "extract":
                        pages_option = options.get("pages")
                        if pages_option is None:
                            raise InvalidRangeError("Pages option is required for 'extract' operation")
                        output_filename = str(
                            options.get("output_filename", f"{Path(pdf_file).stem}_extracted.pdf")
                        )
                        created_path = splitter.extract_pages(
                            pages=pages_option,  # type: ignore[arg-type]
                            output_path=str(pdf_output_dir / output_filename),
                        )
                        created = [created_path]
                    else:
                        raise InvalidRangeError(f"Unknown operation: {operation}")

                    manifest.mark_success(pdf_file, created)
                    manifest.save()

                    results.append(
                        {
                            "file": pdf_file,
                            "status": "success",
                            "files_created": created,
                            "attempts": entry.attempts,
                            "output_dir": str(pdf_output_dir),
                        }
                    )
                    success_count += 1
                    break
                except (
                    InvalidPDFError,
                    EncryptedPDFError,
                    InvalidRangeError,
                    PageOutOfBoundsError,
                    PDFSplitterException,
                    InsufficientDiskSpaceError,
                ) as exc:
                    attempt_error = str(exc)
                    manifest.mark_failure(pdf_file, attempt_error)
                    manifest.save()

                    if isinstance(exc, (InvalidPDFError, EncryptedPDFError, InvalidRangeError, PageOutOfBoundsError)):
                        results.append(
                            {
                                "file": pdf_file,
                                "status": "failure",
                                "error": attempt_error,
                                "attempts": entry.attempts,
                                "output_dir": str(pdf_output_dir),
                            }
                        )
                        failure_count += 1
                        break

                    allowed_attempts = self.max_retries + 1
                    if entry.attempts >= allowed_attempts:
                        results.append(
                            {
                                "file": pdf_file,
                                "status": "failure",
                                "error": attempt_error,
                                "attempts": entry.attempts,
                                "output_dir": str(pdf_output_dir),
                            }
                        )
                        failure_count += 1
                        break

                    if self.retry_backoff_seconds:
                        time.sleep(self.retry_backoff_seconds)
                    continue

        total_attempts = sum(manifest.get(file).attempts for file in pdf_files if file in manifest)

        return BatchResult(
            total=len(pdf_files),
            success=success_count,
            failure=failure_count,
            skipped=skipped_count,
            results=results,
            manifest_path=str(manifest_path),
            total_attempts=total_attempts,
        )


__all__ = [
    "PDFSplitter",
    "BatchProcessor",
    "parse_ranges",
    "parse_page_spec",
    "validate_ranges",
]
