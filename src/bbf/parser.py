from __future__ import annotations

import sys
from dataclasses import dataclass, field
from enum import StrEnum, auto

from bbf.lexer import Lexer, Position, Token, TokenType
from bbf.utils import eprint


class ParserExpectError(Exception):
    def __init__(self, got: TokenType, expected: TokenType, pos: Position) -> None:
        self.got = got
        self.expected = expected
        self.pos = pos

    def __str__(self) -> str:
        return f"ERROR: {self.pos} Expected {self.expected}, but got {self.got}"


class Parser:
    # TODO: input lexer instead?
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.index = 0

    def peek(self) -> Token:
        if self.index + 1 >= len(self.tokens):
            return Token(
                TokenType.EOF, value="", position=Position(Path(), line=-1, column=-1)
            )
        return self.tokens[self.index + 1]

    def advance(self) -> Token:
        if self.index >= len(self.tokens):
            return Token(
                TokenType.EOF, value="", position=Position(Path(), line=-1, column=-1)
            )
        self.index += 1
        return (
            self.tokens[self.index]
            if self.index < len(self.tokens)
            else Token(
                TokenType.EOF, value="", position=Position(Path(), line=-1, column=-1)
            )
        )

    def parse(self) -> FunctionCallNode:
        return self.parse_function_call()

    def parse_function_call(self) -> FunctionCallNode:
        if (
            self.current_token.ttype != TokenType.Identifier
            and self.current_token.value != "exit"
        ):
            raise ValueError(
                f"expected 'exit' function, but got {self.current_token.value}"
            )
        name = self.current_token.value
        self.advance()

        self.expect(TokenType.Lparen)
        self.advance()

        self.expect(TokenType.Integer)
        value = int(self.current_token.value)
        self.advance()

        self.expect(TokenType.Rparen)
        self.advance()

        return FunctionCallNode(name=name, args=[value])

    def expect(self, ttype: TokenType) -> None:
        if self.current_token.ttype != ttype:
            raise ParserExpectError(
                got=self.current_token.ttype,
                expected=ttype,
                pos=self.current_token.position,
            )

    @property
    def current_token(self) -> Token:
        return self.tokens[self.index]


@dataclass
class FunctionCallNode:
    name: str
    args: list[str]
