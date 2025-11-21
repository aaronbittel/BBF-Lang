from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bbf.lexer import Token
from bbf.nodes.stmt import Block, Stmt
from bbf.varinfo import VarType

if TYPE_CHECKING:
    from bbf.nodes.visitor import Visitor


class TopLevel(ABC):
    @abstractmethod
    def accept[T](self, visitor: Visitor[T]) -> T: ...


@dataclass
class FnDef(TopLevel):
    name: Token
    params: list[Param]
    ret_vartype: VarType
    body: Block

    def accept[T](self, visitor: Visitor[T]) -> T:
        return visitor.visit_fndef(self)


@dataclass
class TopLevelStmt(TopLevel):
    stmt: Stmt

    def accept[T](self, visitor: Visitor[T]) -> T:
        return visitor.visit_toplevelstmt(self)


@dataclass
class Param:
    name: Token
    ttype: Token
