"""Core interfaces and context objects shared by IntelliPDF tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from ...core.parser import PDFParser
from ...core.utils import resolve_path


@dataclass
class ConversionContext:
    """Holds shared execution state for a tool invocation."""

    input_path: Path | None = None
    output_path: Path | None = None
    parser: PDFParser | None = None
    resources: dict[str, Any] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.input_path, (str, Path)) and self.input_path is not None:
            self.input_path = resolve_path(self.input_path)
        if isinstance(self.output_path, (str, Path)) and self.output_path is not None:
            self.output_path = resolve_path(self.output_path)

    def ensure_parser(self) -> PDFParser:
        if self.parser is None:
            if self.input_path is None:
                raise ValueError("ConversionContext requires an input_path to create a parser")
            self.parser = PDFParser(self.input_path)
        return self.parser

    def with_updates(
        self,
        *,
        input_path: str | Path | None = None,
        output_path: str | Path | None = None,
        config: dict[str, Any] | None = None,
    ) -> "ConversionContext":
        data = ConversionContext(
            input_path=input_path or self.input_path,
            output_path=output_path or self.output_path,
            parser=self.parser,
            resources=dict(self.resources),
            config=dict(self.config),
        )
        if config:
            data.config.update(config)
        return data


class BaseTool:
    """Base class for all pluggable IntelliPDF tools."""

    name: str

    def __init__(self, context: ConversionContext) -> None:
        self.context = context

    @classmethod
    def configure_parser(cls, parser: Any) -> None:  # pragma: no cover - optional hook
        """Hook allowing tools to extend CLI parsers."""

    def run(self) -> Any:  # pragma: no cover - to be implemented by subclasses
        raise NotImplementedError


ToolFactory = Callable[[ConversionContext], BaseTool]
