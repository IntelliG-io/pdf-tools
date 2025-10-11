"""Password protection helpers for the :mod:`intellipdf` toolkit."""

from __future__ import annotations

from pathlib import Path
from pypdf import PdfReader, PdfWriter

PathLike = str | Path


class PdfSecurityError(Exception):
    """Raised when PDF password operations fail."""


def _ensure_path(path: PathLike) -> Path:
    return Path(path).expanduser().resolve()


def _copy_reader_contents(reader: PdfReader) -> PdfWriter:
    writer = PdfWriter()
    writer.clone_reader_document_root(reader)

    metadata = reader.metadata
    if metadata:
        writer.add_metadata(
            {
                key: str(value)
                for key, value in metadata.items()
                if isinstance(key, str) and value is not None
            }
        )

    return writer


def is_pdf_encrypted(path: PathLike) -> bool:
    """Return ``True`` when ``path`` points to an encrypted PDF document."""

    pdf_path = _ensure_path(path)
    try:
        reader = PdfReader(str(pdf_path))
    except FileNotFoundError as exc:  # pragma: no cover - delegated to caller
        raise PdfSecurityError(f"PDF not found: {pdf_path}") from exc
    except Exception as exc:  # pragma: no cover - pypdf exceptions vary
        raise PdfSecurityError(f"Unable to read PDF: {pdf_path}") from exc

    return bool(reader.is_encrypted)


def protect_pdf(
    input: PathLike,
    output: PathLike,
    password: str,
    *,
    owner_password: str | None = None,
) -> Path:
    """Encrypt ``input`` with ``password`` and write the result to ``output``."""

    if not password:
        raise PdfSecurityError("A non-empty password is required")

    input_path = _ensure_path(input)
    output_path = _ensure_path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        reader = PdfReader(str(input_path))
    except FileNotFoundError as exc:
        raise PdfSecurityError(f"PDF not found: {input_path}") from exc
    except Exception as exc:  # pragma: no cover - pypdf exceptions vary
        raise PdfSecurityError(f"Unable to read PDF: {input_path}") from exc

    if reader.is_encrypted:
        raise PdfSecurityError("Input PDF is already encrypted")

    writer = _copy_reader_contents(reader)

    try:
        writer.encrypt(
            user_password=password,
            owner_password=owner_password or password,
        )
    except Exception as exc:  # pragma: no cover - encryption errors vary
        raise PdfSecurityError("Failed to encrypt PDF") from exc

    try:
        with output_path.open("wb") as stream:
            writer.write(stream)
    except Exception as exc:  # pragma: no cover - IO errors vary
        raise PdfSecurityError(f"Unable to write PDF to {output_path}") from exc

    return output_path


def unprotect_pdf(
    input: PathLike,
    output: PathLike,
    password: str,
) -> Path:
    """Decrypt ``input`` using ``password`` and write the result to ``output``."""

    if not password:
        raise PdfSecurityError("A non-empty password is required")

    input_path = _ensure_path(input)
    output_path = _ensure_path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        reader = PdfReader(str(input_path))
    except FileNotFoundError as exc:
        raise PdfSecurityError(f"PDF not found: {input_path}") from exc
    except Exception as exc:  # pragma: no cover - pypdf exceptions vary
        raise PdfSecurityError(f"Unable to read PDF: {input_path}") from exc

    if not reader.is_encrypted:
        raise PdfSecurityError("Input PDF is not encrypted")

    try:
        status = reader.decrypt(password)
    except Exception as exc:  # pragma: no cover - decrypt errors vary
        raise PdfSecurityError("Failed to decrypt PDF") from exc

    if status == 0:
        raise PdfSecurityError("Incorrect password for encrypted PDF")

    writer = _copy_reader_contents(reader)

    try:
        with output_path.open("wb") as stream:
            writer.write(stream)
    except Exception as exc:  # pragma: no cover - IO errors vary
        raise PdfSecurityError(f"Unable to write PDF to {output_path}") from exc

    return output_path


__all__ = [
    "PdfSecurityError",
    "protect_pdf",
    "unprotect_pdf",
    "is_pdf_encrypted",
]
