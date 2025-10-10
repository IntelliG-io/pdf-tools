"""Backward compatibility layer for the legacy :mod:`pdfmergex` package."""

from __future__ import annotations

from intellipdf.merge import *  # noqa: F401,F403

from . import merger  # noqa: F401  (re-export for attribute access)
