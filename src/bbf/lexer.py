from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, auto
from pathlib import Path


class TokenType(StrEnum):
    Identifier = auto()
    IntegerLit = auto()
    StringLit = auto()

    # Types
    Int = auto()
    String = auto()

    # Builtin Functions
    Exit = auto()
    Print = auto()
    Eprint = auto()
    Atoi = auto()

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

    # Double Char Tokens
    GreaterEqual = auto()
    LessEqual = auto()
    EqualEqual = auto()
    BangEqual = auto()

    Illegal = auto()
    EOF = auto()


BUILTINS = {
    # Builtin Functions
    "exit": TokenType.Exit,
    "print": TokenType.Print,
    "eprint": TokenType.Eprint,
    "atoi": TokenType.Atoi,
    # Types
    "String": TokenType.String,
    "Int": TokenType.Int,
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
            return self._create_token(ttype=TokenType.EOF, value="EOF", length=0)

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
        elif ch == ">":
            if self.peek(1) == "=":
                token = self._create_token(
                    ttype=TokenType.GreaterEqual, value=">=", length=2
                )
                self.advance()  # advance `=`
            else:
                token = self._create_token(ttype=TokenType.Greater, value=">")
            self.advance()
        elif ch == "<":
            if self.peek(1) == "=":
                token = self._create_token(
                    ttype=TokenType.LessEqual, value="<=", length=2
                )
                self.advance()  # advance `=`
            else:
                token = self._create_token(ttype=TokenType.Less, value="<")
            self.advance()
        elif ch == "=":
            if self.peek(1) == "=":
                token = self._create_token(
                    ttype=TokenType.EqualEqual, value="==", length=2
                )
                self.advance()  # advance `=`
            else:
                token = self._create_token(ttype=TokenType.Equal, value="=")
            self.advance()
        elif ch == "!":
            if self.peek(1) == "=":
                token = self._create_token(
                    ttype=TokenType.BangEqual, value="!=", length=2
                )
                self.advance()  # advance `=`
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

        # TODO: probably some edge cases here
        if not self.char.isalpha():
            return self._create_token(
                ttype=TokenType.IntegerLit, value=num_str, length=self.index - start
            )

        # illegal integer literal
        while self.char.isalnum():
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
        while self.char.isalnum() or self.char == "_":
            self.advance()
        identifier = self.src[start : self.index]
        ttype = TokenType.Identifier
        if identifier in BUILTINS:
            ttype = BUILTINS[identifier]
        return self._create_token(ttype=ttype, value=identifier, length=len(identifier))

    def read_string_literal(self) -> Token:
        # NOTE: Handle escape sequences "\n" here?
        start = self.index
        self.advance()  # advance '"'
        string = ""
        while self.char != "" and self.char.isascii() and not self.char == '"':
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
        self.advance()  # advance '"'
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
