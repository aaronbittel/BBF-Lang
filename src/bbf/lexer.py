from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, auto
from pathlib import Path

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

        if self.index >= len(self.src):
            return self._create_token(ttype=TokenType.EOF, value="EOF")

        ch = self.char

        if ch == "#":  # comment
            self.skip_comment()
            return self.next_token()

        if ch == "(":
            token = self._create_token(ttype=TokenType.OpenParen, value="(")
            self.advance()
        elif ch == ")":
            token = self._create_token(ttype=TokenType.CloseParen, value=")")
            self.advance()
        elif ch == "=":
            token = self._create_token(ttype=TokenType.Assign, value="=")
            self.advance()
        elif ch == "+":
            token = self._create_token(ttype=TokenType.Plus, value="+")
            self.advance()
        elif ch == "-":
            token = self._create_token(ttype=TokenType.Minus, value="-")
            self.advance()
        elif ch == "*":
            token = self._create_token(ttype=TokenType.Multiplication, value="*")
            self.advance()
        elif ch == "/":
            token = self._create_token(ttype=TokenType.Division, value="/")
            self.advance()
        elif ch.isnumeric():
            token = self.read_number()
        elif ch.isalpha():
            token = self.read_identifier()
        elif ch == '"':
            token = self.read_string_literal()
        else:
            token = self._create_token(ttype=TokenType.Illegal, value="")

        # if token.ttype == TokenType.Illegal:
        #     raise LexerError(msg=f"invalid character {ch}", position=self.position)
        return token

    def read_number(self) -> Token:
        start = self.index
        self.advance()  # first digit
        while self.char.isnumeric():
            self.advance()

        # TODO: probably some edge cases here
        if not self.char.isalpha():
            num = self.src[start : self.index]
            return self._create_token(ttype=TokenType.Illegal, value=value)

        # illegal integer literal
        while self.char.isalnum():
            self.advance()
        value = self.src[start : self.index]
        self.errors.append(
            LexerError(msg=f"invalid integer literal '{value}'", position=self.position)
        )
        return self._create_token(ttype=TokenType.Illegal, value=value)

    def read_identifier(self) -> Token:
        start = self.index
        self.advance()  # first character
        while self.char.isalnum() or self.char == "_":
            self.advance()
        identifier = self.src[start : self.index]
        ttype = TokenType.Exit if identifier == "exit" else TokenType.Identifier
        return self._create_token(ttype=ttype, value=identifier)

    def read_string_literal(self) -> Token:
        self.advance()  # advance '"'
        start = self.index
        while self.char != "" and self.char.isascii() and not self.char == '"':
            self.advance()

        if self.char == "":  # EOF
            raise LexerError(msg="unterminated string literal", position=self.position)
        string = self.src[start : self.index]
        token = Token(
            ttype=TokenType.String,
            value=string,
            position=Position(path=self.path, line=self.line, column=start),
        )
        self.column += len(string) + 2  # 2 for "
        self.advance()  # advance '"'
        return token

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
    for token in tokens:
        print(token)
