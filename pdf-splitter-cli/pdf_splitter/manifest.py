"""Manifest support for resumable batch PDF processing."""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


@dataclass
class ManifestEntry:
    """Represents the processing status for a single PDF."""

    file: str
    status: str = "pending"
    attempts: int = 0
    error: Optional[str] = None
    files_created: List[str] = field(default_factory=list)
    last_updated: str = field(default_factory=_utc_now)

    def mark(self, *, status: str, error: Optional[str] = None, files_created: Optional[Iterable[str]] = None) -> None:
        self.status = status
        self.error = error
        if files_created is not None:
            self.files_created = list(files_created)
        self.last_updated = _utc_now()

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class BatchManifest:
    """Load, update, and persist batch processing manifests."""

    VERSION = 1

    def __init__(self, path: Path, entries: Optional[Dict[str, ManifestEntry]] = None) -> None:
        self.path = path
        self.entries: Dict[str, ManifestEntry] = entries or {}

    @classmethod
    def load(cls, path: Path, *, create: bool = True) -> "BatchManifest":
        if path.exists():
            data = json.loads(path.read_text())
            version = data.get("version", 0)
            if version != cls.VERSION:
                raise ValueError(f"Unsupported manifest version: {version}")
            entries = {
                key: ManifestEntry(**value)
                for key, value in data.get("entries", {}).items()
            }
            return cls(path=path, entries=entries)
        if not create:
            raise FileNotFoundError(path)
        return cls(path=path)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": self.VERSION,
            "entries": {key: entry.to_dict() for key, entry in self.entries.items()},
        }
        with tempfile.NamedTemporaryFile("w", delete=False, dir=self.path.parent, suffix=".tmp") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            temp_path = Path(handle.name)
        temp_path.replace(self.path)

    def get(self, file: str) -> ManifestEntry:
        entry = self.entries.get(file)
        if entry is None:
            entry = ManifestEntry(file=file)
            self.entries[file] = entry
        return entry

    def increment_attempt(self, file: str) -> ManifestEntry:
        entry = self.get(file)
        entry.attempts += 1
        entry.mark(status="in-progress")
        return entry

    def mark_success(self, file: str, files_created: Iterable[str]) -> ManifestEntry:
        entry = self.get(file)
        entry.mark(status="success", error=None, files_created=list(files_created))
        return entry

    def mark_failure(self, file: str, error: str) -> ManifestEntry:
        entry = self.get(file)
        entry.mark(status="failure", error=error)
        return entry

    def should_skip(self, file: str) -> bool:
        entry = self.entries.get(file)
        return entry is not None and entry.status == "success"

    def stats_for(self, files: Iterable[str]) -> Dict[str, int]:
        success = 0
        failure = 0
        skipped = 0
        for file in files:
            entry = self.entries.get(file)
            if not entry:
                continue
            if entry.status == "success":
                success += 1
            elif entry.status == "failure":
                failure += 1
            elif entry.status == "skipped":
                skipped += 1
        return {"success": success, "failure": failure, "skipped": skipped}
    def __contains__(self, file: str) -> bool:
        return file in self.entries
