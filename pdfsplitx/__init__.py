"""Backward compatibility layer for the legacy :mod:`pdfsplitx` package."""

from __future__ import annotations

from intellipdf.split import *  # noqa: F401,F403

from . import splitter  # noqa: F401  (re-export for attribute access)
