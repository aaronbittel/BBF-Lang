from pathlib import Path
from typing import Callable

import pytest

from bbf.lexer import Lexer, Position, Token, TokenType


TEST_PATH = Path("testing.bbf")


def p(line: int = 1, column: int = 1) -> Position:
    return Position(path=TEST_PATH, line=line, column=column)


def t(ttype: TokenType, value: str, line: int = 1, column: int = 1) -> Token:
    return Token(ttype=ttype, value=value, position=p(line, column))


def minus(line: int = 1, column: int = 1) -> Token:
    return t(ttype=TokenType.Minus, value="-", line=line, column=column)


def plus(line: int = 1, column: int = 1) -> Token:
    return t(ttype=TokenType.Plus, value="+", line=line, column=column)


def mult(line: int = 1, column: int = 1) -> Token:
    return t(ttype=TokenType.Multiplication, value="*", line=line, column=column)


def div(line: int = 1, column: int = 1) -> Token:
    return t(ttype=TokenType.Division, value="/", line=line, column=column)


def lparen(line: int = 1, column: int = 1) -> Token:
    return t(ttype=TokenType.Lparen, value="(", line=line, column=column)


def rparen(line: int = 1, column: int = 1) -> Token:
    return t(ttype=TokenType.Rparen, value=")", line=line, column=column)


def eof(line: int = 1, column: int = 1) -> Token:
    return t(ttype=TokenType.EOF, value="", line=line, column=column)


def integer(value: int, line: int = 1, column: int = 1) -> Token:
    return t(ttype=TokenType.Integer, value=str(value), line=line, column=column)


def string(value: str, line: int = 1, column: int = 1) -> Token:
    return t(ttype=TokenType.String, value=value, line=line, column=column)


def ident(value: str, line: int = 1, column: int = 1) -> Token:
    return t(ttype=TokenType.Identifier, value=value, line=line, column=column)


def assign(line: int = 1, column: int = 1) -> Token:
    return t(ttype=TokenType.Assign, value="=", line=line, column=column)
