from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, auto

from bbf.span import Position


@dataclass
class Token:
    ttype: TokenType
    value: str
    position: Position

    def __str__(self) -> str:
        return f"{self.ttype.value.capitalize()}[{self.position}] => {self.value!r}"


class TokenType(StrEnum):
    Identifier = auto()
    IntegerLit = auto()
    StringLit = auto()
    BoolTrue = auto()
    BoolFalse = auto()

    # Types
    Int = auto()
    String = auto()
    Void = auto()
    Bool = auto()

    # Keywords
    If = auto()
    Then = auto()
    Else = auto()
    End = auto()
    Not = auto()
    Elif = auto()
    For = auto()
    Do = auto()
    In = auto()
    Fn = auto()
    Return = auto()
    Or = auto()
    And = auto()

    # Single Char Tokens
    OpenParen = auto()
    CloseParen = auto()
    OpenBracket = auto()
    CloseBracket = auto()
    Equal = auto()
    Plus = auto()
    Minus = auto()
    Star = auto()
    Slash = auto()
    Percent = auto()
    Colon = auto()
    Greater = auto()
    Less = auto()
    Dot = auto()
    Comma = auto()

    # Double Char Tokens
    GreaterEqual = auto()
    LessEqual = auto()
    EqualEqual = auto()
    BangEqual = auto()

    Illegal = auto()
    EOF = auto()


BUILTINS = {
    # Types
    "String": TokenType.String,
    "Int": TokenType.Int,
    "Void": TokenType.Void,
    "Bool": TokenType.Bool,
    # Values
    "true": TokenType.BoolTrue,
    "false": TokenType.BoolFalse,
    # Keywords
    "if": TokenType.If,
    "then": TokenType.Then,
    "end": TokenType.End,
    "not": TokenType.Not,
    "else": TokenType.Else,
    "elif": TokenType.Elif,
    "for": TokenType.For,
    "do": TokenType.Do,
    "in": TokenType.In,
    "fn": TokenType.Fn,
    "return": TokenType.Return,
    "or": TokenType.Or,
    "and": TokenType.And,
}


def dump_tokens(tokens: list[Token]) -> None:
    for token in tokens:
        print(token)
