from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bbf.nodes.toplevel import TopLevel

if TYPE_CHECKING:
    from bbf.nodes.visitor import Visitor


class Program(ABC):
    @abstractmethod
    def accept(self, visitor: Visitor) -> None: ...


@dataclass
class ProgTopLevelStmt(Program):
    stmts: list[TopLevel]

    def accept(self, visitor: Visitor) -> None:
        return visitor.visit_progtoplevelstmt(self)
