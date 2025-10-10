"""
Type definitions and dataclasses for PDF Splitter.

This module defines data structures used throughout the library.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PDFInfo:
    """
    PDF document information and metadata.

    Attributes:
        num_pages: Number of pages in the PDF
        file_size: File size in bytes
        title: PDF title metadata
        author: PDF author metadata
        subject: PDF subject metadata
        creator: PDF creator application
        producer: PDF producer application
        is_encrypted: Whether the PDF is encrypted
        linearized: Whether the PDF is linearized for fast web view
        has_outlines: Whether the PDF contains outlines/bookmarks
        fonts: List of font names referenced in the document
        attachments: Number of embedded files
        xmp_metadata: Raw XMP metadata if present
    """
    num_pages: int
    file_size: int
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    is_encrypted: bool = False
    linearized: bool = False
    has_outlines: bool = False
    fonts: List[str] = field(default_factory=list)
    attachments: int = 0
    xmp_metadata: Optional[str] = None


@dataclass
class SplitResult:
    """
    Result of a PDF split operation.
    
    Attributes:
        success: Whether the operation was successful
        files_created: List of created file paths
        total_files: Total number of files created
        source_file: Path to source PDF file
        operation: Type of operation performed
        error: Error message if operation failed
    """
    success: bool
    files_created: List[str]
    total_files: int
    source_file: str
    operation: str
    error: Optional[str] = None
    
    def __str__(self) -> str:
        """String representation of the result."""
        if self.success:
            return f"SplitResult(success=True, files={self.total_files})"
        else:
            return f"SplitResult(success=False, error='{self.error}')"


@dataclass
class BatchResult:
    """
    Result of a batch processing operation.
    
    Attributes:
        total: Total number of PDFs processed
        success: Number of successfully processed PDFs
        failure: Number of failed PDFs
        results: List of individual results
    """
    total: int
    success: int
    failure: int
    skipped: int = 0
    results: List[Dict[str, Any]] = field(default_factory=list)
    manifest_path: Optional[str] = None
    total_attempts: int = 0
    
    def __str__(self) -> str:
        """String representation of the result."""
        return (
            "BatchResult(total={total}, success={success}, failure={failure}, "
            "skipped={skipped}, attempts={attempts})"
        ).format(
            total=self.total,
            success=self.success,
            failure=self.failure,
            skipped=self.skipped,
            attempts=self.total_attempts,
        )
