"""Utilities shared by IntelliPDF tools."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    return logger


def resolve_path(path: str | Path | None) -> Path:
    if path is None:
        raise ValueError("Path must not be None")
    resolved = Path(path).expanduser().resolve()
    return resolved


def update_dict(target: dict[str, Any], **updates: Any) -> dict[str, Any]:
    target.update({k: v for k, v in updates.items() if v is not None})
    return target
