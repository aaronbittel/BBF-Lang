from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bbf.span import Span
from bbf.token import Token
from bbf.varinfo import VarType

if TYPE_CHECKING:
    from bbf.nodes.visitor import Visitor


@dataclass(kw_only=True)
class Expr(ABC):
    span: Span
    vartype: VarType | None = None

    @abstractmethod
    def accept[T](self, visitor: Visitor[T]) -> T: ...


@dataclass
class Identifier(Expr):
    token: Token

    def accept[T](self, visitor: Visitor[T]) -> T:
        return visitor.visit_identifier(self)


@dataclass
class IntegerLit(Expr):
    token: Token

    def accept[T](self, visitor: Visitor[T]) -> T:
        return visitor.visit_integerlit(self)


@dataclass
class StringLit(Expr):
    token: Token

    def accept[T](self, visitor: Visitor[T]) -> T:
        return visitor.visit_stringlit(self)


@dataclass
class Binary(Expr):
    lhs: Expr
    operator: Token
    rhs: Expr

    def accept[T](self, visitor: Visitor[T]) -> T:
        return visitor.visit_binary(self)


@dataclass
class Unary(Expr):
    operator: Token
    expr: Expr

    def accept[T](self, visitor: Visitor[T]) -> T:
        return visitor.visit_unary(self)


@dataclass
class Grouping(Expr):
    expr: Expr

    def accept[T](self, visitor: Visitor[T]) -> T:
        return visitor.visit_grouping(self)


@dataclass
class Argv(Expr):
    expr: Expr

    def accept[T](self, visitor: Visitor[T]) -> T:
        return visitor.visit_argv(self)


@dataclass
class FnCall(Expr):
    name: Token
    args: list[Expr]

    def accept[T](self, visitor: Visitor[T]) -> T:
        return visitor.visit_fncall(self)


@dataclass
class MethodCall(Expr):
    target: Token
    method: Token
    args: list[Expr]

    def accept[T](self, visitor: Visitor[T]) -> T:
        return visitor.visit_methodcall(self)


@dataclass
class ArrayLiteral(Expr):
    items: list[Expr]

    def accept[T](self, visitor: Visitor[T]) -> T:
        return visitor.visit_array_literal(self)


@dataclass
class Indexing(Expr):
    name: Token
    index: Expr

    def accept[T](self, visitor: Visitor[T]) -> T:
        return visitor.visit_indexing(self)


@dataclass
class RangeIndexing(Expr):
    name: Token
    range_expr: Range

    def accept[T](self, visitor: Visitor[T]) -> T:
        return visitor.visit_range_indexing(self)


@dataclass
class BoolTrue(Expr):
    token: Token

    def accept[T](self, visitor: Visitor[T]) -> T:
        return visitor.visit_booltrue(self)


@dataclass
class BoolFalse(Expr):
    token: Token

    def accept[T](self, visitor: Visitor[T]) -> T:
        return visitor.visit_boolfalse(self)


@dataclass
class Range:
    start: Expr
    stop: Expr
    inclusive: bool
