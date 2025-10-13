"""Plugin registry and orchestration helpers for IntelliPDF tools."""

from __future__ import annotations

from typing import Dict, Iterable

from .interfaces import BaseTool, ConversionContext, ToolFactory


class ToolRegistry:
    """Registry storing available IntelliPDF tools."""

    def __init__(self) -> None:
        self._tools: Dict[str, type[BaseTool]] = {}

    def register(self, name: str, tool_class: type[BaseTool]) -> None:
        if name in self._tools:
            raise ValueError(f"Tool '{name}' is already registered")
        self._tools[name] = tool_class

    def create(self, name: str, context: ConversionContext) -> BaseTool:
        try:
            tool_class = self._tools[name]
        except KeyError as exc:  # pragma: no cover - defensive branch
            raise KeyError(f"Tool '{name}' is not registered") from exc
        return tool_class(context)

    def names(self) -> Iterable[str]:
        return sorted(self._tools.keys())

    def get(self, name: str) -> type[BaseTool] | None:
        return self._tools.get(name)


registry = ToolRegistry()


def register_tool(name: str):
    def decorator(cls: type[BaseTool]) -> type[BaseTool]:
        registry.register(name, cls)
        return cls

    return decorator


__all__ = ["ToolRegistry", "registry", "register_tool", "ConversionContext", "BaseTool", "ToolFactory"]
