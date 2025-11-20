from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bbf.lexer import Token

if TYPE_CHECKING:
    from bbf.nodes.visitor import Visitor


class Expr(ABC):
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
    args_list: list[Expr]

    def accept[T](self, visitor: Visitor[T]) -> T:
        return visitor.visit_fncall(self)


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
