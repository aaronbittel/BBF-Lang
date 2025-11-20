from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, auto
from pathlib import Path

from bbf.source import Source


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
}


class LexerError(Exception):
    def __init__(self, msg: str, position: Position) -> None:
        self.msg = msg
        self.position = position

    def __str__(self) -> str:
        return f"ERROR: {self.position}: {self.msg}"


@dataclass
class Token:
    ttype: TokenType
    value: str
    position: Position

    def __str__(self) -> str:
        return f"{self.ttype.value.capitalize()}[{self.position}] => {self.value!r}"


class Lexer:
    def __init__(self, source: Source) -> None:
        self.source = source
        self.index = 0

        self.line = 1
        self.column = 1
        self.errors: list[LexerError] = []

    def tokenize(self) -> list[Token]:
        """Collecting all tokens from the input, ending with Token EOF."""
        tokens: list[Token] = []
        while token := self.next_token():
            tokens.append(token)
            if token.ttype == TokenType.EOF:
                break
        return tokens

    def next_token(self) -> Token:
        self.skip_whitespace()

        if self.is_eof():
            return self._create_token(ttype=TokenType.EOF, value="EOF", length=0)

        ch = self.peek()

        if ch == "#":  # comment
            self.skip_comment()
            return self.next_token()

        if ch == "(":
            token = self._create_token(ttype=TokenType.OpenParen, value="(")
            self.advance()
        elif ch == ")":
            token = self._create_token(ttype=TokenType.CloseParen, value=")")
            self.advance()
        elif ch == "[":
            token = self._create_token(ttype=TokenType.OpenBracket, value="[")
            self.advance()
        elif ch == "]":
            token = self._create_token(ttype=TokenType.CloseBracket, value="]")
            self.advance()
        elif ch == "+":
            token = self._create_token(ttype=TokenType.Plus, value="+")
            self.advance()
        elif ch == "-":
            token = self._create_token(ttype=TokenType.Minus, value="-")
            self.advance()
        elif ch == "*":
            token = self._create_token(ttype=TokenType.Star, value="*")
            self.advance()
        elif ch == "/":
            token = self._create_token(ttype=TokenType.Slash, value="/")
            self.advance()
        elif ch == "%":
            token = self._create_token(ttype=TokenType.Percent, value="%")
            self.advance()
        elif ch == ":":
            token = self._create_token(ttype=TokenType.Colon, value=":")
            self.advance()
        elif ch == ".":
            token = self._create_token(ttype=TokenType.Dot, value=".")
            self.advance()
        elif ch == ",":
            token = self._create_token(ttype=TokenType.Comma, value=",")
            self.advance()
        elif ch == ">":
            self.advance()
            if self.peek() == "=":
                token = self._create_token(
                    ttype=TokenType.GreaterEqual, value=">=", length=2
                )
                self.consume("=")
            else:
                token = self._create_token(ttype=TokenType.Greater, value=">")
        elif ch == "<":
            self.advance()
            if self.peek() == "=":
                token = self._create_token(
                    ttype=TokenType.LessEqual, value="<=", length=2
                )
                self.consume("=")
            else:
                token = self._create_token(ttype=TokenType.Less, value="<")
        elif ch == "=":
            self.advance()
            if self.peek() == "=":
                token = self._create_token(
                    ttype=TokenType.EqualEqual, value="==", length=2
                )
                self.consume("=")
            else:
                token = self._create_token(ttype=TokenType.Equal, value="=")
        elif ch == "!":
            if self.peek(1) == "=":
                token = self._create_token(
                    ttype=TokenType.BangEqual, value="!=", length=2
                )
                self.consume("=")
            else:
                raise LexerError(
                    msg="single `!` is not allowed. Did you forget `=` for comparison? If you want to negate, use `not` instead.",
                    position=self.position,
                )
            self.advance()
        elif ch.isnumeric():
            token = self.read_number()
        elif ch.isalpha() or ch == "_":
            token = self.read_identifier()
        elif ch == '"':
            token = self.read_string_literal()
        else:
            token = self._create_token(ttype=TokenType.Illegal, value="")
            raise LexerError(msg=f"Illegal Token `{ch}`", position=token.position)

        return token

    def read_number(self) -> Token:
        start = self.index
        num_str = self.advance()  # first digit
        while (ch := self.peek()) and ch.isnumeric() or ch == "_":
            if ch == "_":
                if self.previous() == "_":
                    raise LexerError(
                        msg="SyntaxError: invalid decimal literal: consecutive `_` are not allowed",
                        position=self.position,
                    )
                self.advance()
                continue
            num_str += self.advance()

        # NOTE: maybe some edge cases here?
        if not self.peek().isalpha():
            return self._create_token(
                ttype=TokenType.IntegerLit, value=num_str, length=self.index - start
            )

        # illegal integer literal
        while self.peek().isalnum():
            self.advance()
        value = self.src[start : self.index]
        self.errors.append(
            LexerError(msg=f"invalid integer literal '{value}'", position=self.position)
        )
        return self._create_token(
            ttype=TokenType.Illegal, value=value, length=len(value)
        )

    def read_identifier(self) -> Token:
        start = self.index
        self.advance()  # first character
        while (ch := self.peek()) and ch.isalnum() or ch == "_":
            self.advance()
        identifier = self.src[start : self.index]
        ttype = TokenType.Identifier
        if identifier in BUILTINS:
            ttype = BUILTINS[identifier]
        return self._create_token(ttype=ttype, value=identifier, length=len(identifier))

    def read_string_literal(self) -> Token:
        start = self.index
        self.consume('"')
        string = ""
        while (ch := self.peek()) and ch != "" and ch.isascii() and not ch == '"':
            ch = self.advance()
            if ch == "\\":
                next_ch = self.advance()
                if next_ch == "n":
                    string += "\n"
                elif next_ch == "t":
                    string += "\t"
                elif next_ch == "\\":
                    string += "\\"
                elif next_ch == '"':
                    string += '"'
                elif next_ch == "'":
                    string += "'"
                else:
                    raise LexerError(
                        msg=f"invalid esacpe sequence '{ch + next_ch}'",
                        position=self.position,
                    )
            else:
                string += ch

        if self.is_eof():
            raise LexerError(msg="unterminated string literal", position=self.position)
        self.consume('"')
        return self._create_token(
            ttype=TokenType.StringLit, value=string, length=self.index - start
        )

    def peek(self, offset: int = 0) -> str:
        if self.index + offset >= len(self.src):
            return ""
        return self.src[self.index + offset]

    def advance(self) -> str:
        if self.is_eof():
            return self.previous()
        self.index += 1
        return self.previous()

    def consume(self, ch: str) -> str:
        if self.peek() == ch:
            return self.advance()
        raise LexerError(
            msg=f"Expected `{ch}`, but found {self.peek()}", position=self.position
        )

    def previous(self) -> str:
        return self.src[self.index - 1]

    def is_eof(self) -> bool:
        return self.index >= len(self.src)

    def _create_token(self, ttype: TokenType, value: str, length: int = 1) -> Token:
        position = self.position
        self.column += length
        return Token(ttype=ttype, value=value, position=position)

    def skip_whitespace(self) -> None:
        # TODO: How to handle \r\n?
        while (ch := self.peek()) and ch in (" ", "\n", "\r", "\t"):
            if ch == "\r":
                if self.advance() == "\n":
                    self.advance()
                self.line += 1
                self.column = 1
            elif ch == "\n":
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            self.advance()

    def skip_comment(self) -> None:
        while self.peek() != "" and self.peek() != "\n":
            self.advance()

    @property
    def position(self) -> Position:
        return Position(source=self.source, line=self.line, column=self.column)

    @property
    def src(self) -> str:
        return self.source.text

    @property
    def path(self) -> Path:
        return self.source.filepath


@dataclass
class Position:
    source: Source
    line: int
    column: int

    def __str__(self) -> str:
        return f"{self.source.filepath}:{self.line}:{self.column}"


def dump_tokens(tokens: list[Token]) -> None:
    for token in tokens:
        print(token)
