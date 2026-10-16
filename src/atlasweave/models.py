"""Shared tabular contract; adapters do not depend on matching or export code."""

from dataclasses import dataclass
from typing import Protocol


class AtlasWeaveError(ValueError):
    """An actionable input or workflow error, safe to display without a traceback."""


@dataclass(frozen=True)
class ReadOptions:
    sheet: str | None = None
    delimiter: str = ","
    header_row: int = 1
    max_rows: int = 10_000

    def __post_init__(self):
        if len(self.delimiter) != 1 or self.delimiter in '\r\n"':
            raise AtlasWeaveError("Delimiter must be one character, excluding quote/newline.")
        if not 1 <= self.header_row <= 10_000:
            raise AtlasWeaveError("Header row must be between 1 and 10000.")
        if not 1 <= self.max_rows <= 100_000:
            raise AtlasWeaveError("Row limit must be between 1 and 100000.")


@dataclass(frozen=True)
class Dataset:
    name: str
    fields: tuple[str, ...]
    rows: tuple[tuple[str | None, ...], ...]
    complete: bool
    warnings: tuple[str, ...] = ()

    def column(self, index: int) -> tuple[str | None, ...]:
        return tuple(row[index] for row in self.rows)


class SourceAdapter(Protocol):
    """Future SQL/document adapters must expose explicit tabular selections."""

    storage: str
    format: str
    shape: str

    def discover(self, path: str) -> list[str]: ...

    def read(self, path: str, options: ReadOptions) -> Dataset: ...
