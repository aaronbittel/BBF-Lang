from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple, Self

if TYPE_CHECKING:
    from bbf.token import Token


class Source(NamedTuple):
    text: str
    filepath: Path


@dataclass
class Position:
    source: Source = field(repr=False)
    line: int
    column: int

    def __str__(self) -> str:
        return f"{self.source.filepath}:{self.line}:{self.column}"


@dataclass
class Span:
    start: Position
    end: Position

    @classmethod
    def from_token(cls, token: Token) -> Self:
        return cls(
            token.position,
            Position(
                token.position.source,
                token.position.line,
                token.position.column + len(token.value),
            ),
        )
