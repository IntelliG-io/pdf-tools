"""Backward compatibility layer for the legacy :mod:`pdfcompressx` package."""

from __future__ import annotations

from intellipdf.compress import *  # noqa: F401,F403

from . import compressor  # noqa: F401  (re-export for attribute access)
