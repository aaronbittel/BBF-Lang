from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterator

from bbf.lexer import Token
from bbf.nodes.expr import Expr
from bbf.varinfo import VarType

if TYPE_CHECKING:
    from bbf.nodes.visitor import Visitor


class Stmt(ABC):
    @abstractmethod
    def accept[T](self, visitor: Visitor[T]) -> T: ...


@dataclass
class IfStmt(Stmt):
    condition: Expr
    if_block: Block
    elifs: list[ElifStmt]
    else_block: Block = field(default_factory=lambda: Block())

    def accept[T](self, visitor: Visitor[T]) -> T:
        return visitor.visit_ifstmt(self)


@dataclass
class ForStmt(Stmt):
    loop_ident: Token
    range_expr: Range
    block: Block

    def accept[T](self, visitor: Visitor[T]) -> T:
        return visitor.visit_forstmt(self)


@dataclass
class DoBlock(Stmt):
    block: Block

    def accept[T](self, visitor: Visitor[T]) -> T:
        return visitor.visit_doblock(self)


@dataclass
class Declaration(Stmt):
    name: Token
    vartype: VarType
    expr: Expr

    def accept[T](self, visitor: Visitor[T]) -> T:
        return visitor.visit_declaration(self)


@dataclass
class Assignment(Stmt):
    name: Token
    expr: Expr

    def accept[T](self, visitor: Visitor[T]) -> T:
        return visitor.visit_assignment(self)


@dataclass
class ExprStmt(Stmt):
    expr: Expr

    def accept[T](self, visitor: Visitor[T]) -> T:
        return visitor.visit_exprstmt(self)


@dataclass
class ReturnStmt(Stmt):
    expr: Expr | None = None

    def accept[T](self, visitor: Visitor[T]) -> T:
        return visitor.visit_returnstmt(self)


@dataclass
class ArrayAssign(Stmt):
    name: Token
    index: Expr
    expr: Expr

    def accept[T](self, visitor: Visitor[T]) -> T:
        return visitor.visit_array_assignment(self)


@dataclass
class ElifStmt:
    condition: Expr
    block: Block


@dataclass
class Block:
    stmts: list[Stmt] = field(default_factory=list)

    def add(self, stmt: Stmt) -> None:
        self.stmts.append(stmt)

    def __len__(self) -> int:
        return len(self.stmts)

    def __iter__(self) -> Iterator[Stmt]:
        return iter(self.stmts)


@dataclass
class Range:
    start: Expr
    stop: Expr
    inclusive: bool
