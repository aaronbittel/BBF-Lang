from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, auto
from pathlib import Path

from bbf.utils import eprint

BUILTINS = {"exit"}


class TokenType(StrEnum):
    Integer = auto()
    Identifier = auto()
    String = auto()

    # Builtins
    Exit = auto()

    # Double Char Tokens

    # Single Char Tokens
    OpenParen = auto()
    CloseParen = auto()
    Assign = auto()
    Plus = auto()
    Minus = auto()
    Multiplication = auto()
    Division = auto()

    Illegal = auto()
    EOF = auto()


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
        return f"{self.ttype.value.capitalize()}[{self.position}] => {self.value}"


class Lexer:
    def __init__(self, path: Path, src: str) -> None:
        self.path = path
        self.src = src
        self.index = 0

        self.line = 1
        self.column = 1

    def next_token(self) -> Token:
        self.skip_whitespace()

        if self.index >= len(self.src):
            return self._create_token(ttype=TokenType.EOF, value="EOF")

        ch = self.char

        if ch == "#":  # comment
            self.skip_comment()
            return self.next_token()

        if ch == "(":
            tok = self._create_token(ttype=TokenType.OpenParen, value="(")
            self.advance()
        elif ch == ")":
            tok = self._create_token(ttype=TokenType.CloseParen, value=")")
            self.advance()
        elif ch == "=":
            tok = self._create_token(ttype=TokenType.Assign, value="=")
            self.advance()
        elif ch == "+":
            tok = self._create_token(ttype=TokenType.Plus, value="+")
            self.advance()
        elif ch == "-":
            tok = self._create_token(ttype=TokenType.Minus, value="-")
            self.advance()
        elif ch == "*":
            tok = self._create_token(ttype=TokenType.Multiplication, value="*")
            self.advance()
        elif ch == "/":
            tok = self._create_token(ttype=TokenType.Division, value="/")
            self.advance()
        elif ch.isnumeric():
            tok = self.read_number()
            if self.char.isalpha():
                raise LexerError(msg="invalid integer literal", position=self.position)
        elif ch.isalpha():
            tok = self.read_identifier()
        elif ch == '"':
            tok = self.read_string()
        else:
            tok = self._create_token(ttype=TokenType.Illegal, value="")

        if tok.ttype == TokenType.Illegal:
            raise LexerError(msg=f"invalid character {ch}", position=self.position)
        return tok

    def read_number(self) -> Token:
        start = self.index
        self.advance()  # first digit
        while self.char.isnumeric():
            self.advance()
        num = self.src[start : self.index]
        return self._create_token(ttype=TokenType.Integer, value=num)

    def read_identifier(self) -> Token:
        start = self.index
        self.advance()  # first character
        while self.char.isalnum() or self.char == "_":
            self.advance()
        identifier = self.src[start : self.index]
        ttype = TokenType.Exit if identifier == "exit" else TokenType.Identifier
        return self._create_token(ttype=ttype, value=identifier)

    def read_string(self) -> Token:
        self.advance()  # advance '"'
        start = self.index
        while self.char != "" and self.char.isascii() and not self.char == '"':
            self.advance()

        if self.char == "":  # EOF
            raise LexerError(msg="unterminated string literal", position=self.position)
        string = self.src[start : self.index]
        tok = Token(
            ttype=TokenType.String,
            value=string,
            position=Position(path=self.path, line=self.line, column=start),
        )
        self.column += len(string) + 2  # 2 for "
        self.advance()  # advance '"'
        return tok

    def peek(self) -> str:
        if self.index + 1 >= len(self.src):
            return ""
        return self.src[self.index + 1]

    def advance(self) -> str:
        if self.char == "":
            return ""
        self.index += 1
        return self.src[self.index] if self.index < len(self.src) else ""

    def _create_token(self, ttype: TokenType, value: str) -> Token:
        position = self.position
        if ttype != TokenType.EOF:
            self.column += len(value)
        return Token(ttype=ttype, value=value, position=position)

    def skip_whitespace(self) -> None:
        # TODO: How to handle \r\n?
        while (ch := self.char) and ch in (" ", "\n", "\r", "\t"):
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
        while self.char != "" and self.char != "\n":
            self.advance()

    @property
    def char(self) -> str:
        if self.index >= len(self.src):
            return ""
        return self.src[self.index]

    @property
    def position(self) -> Position:
        return Position(path=self.path, line=self.line, column=self.column)


@dataclass
class Position:
    path: Path
    line: int
    column: int

    def __str__(self) -> str:
        return f"{self.path}:{self.line}:{self.column}"


def dump_tokens(tokens: list[Token]) -> None:
    for tok in tokens:
        print(tok)
