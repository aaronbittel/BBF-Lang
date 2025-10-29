from enum import StrEnum, auto
from dataclasses import dataclass
from pathlib import Path
import sys
from bbf.utils import eprint

BUILTIN_FUNCS = {"exit"}
BUILTIN_KEYWORDS = {}
SEPERATORS = {"(", ")"}


class TokenType(StrEnum):
    BuiltinFunc = auto()
    BuiltinKeyword = auto()
    Integer = auto()
    Ident = auto()
    String = auto()

    # Double Char Tokens

    # Single Char Tokens
    Lparen = auto()
    Rparen = auto()
    Assign = auto()


@dataclass
class Position:
    path: str
    line: int
    row: int


@dataclass
class Token:
    ttype: TokenType
    value: str
    position: Position

    def __str__(self) -> str:
        return f"{self.ttype.value.capitalize()}[{self.position.line}:{self.position.row}] => {self.value}"


def tokenize(path: Path, input: str) -> list[Token]:
    tokens: list[Token] = []
    index = 0

    line = 1
    row = 1

    while index < len(input):
        ch = input[index]
        if ch.isspace():
            if ch == "\n":
                line += 1
                row = 1
            else:
                row += 1
            index += 1
        elif ch.isalpha():
            start = index
            index += 1
            while index < len(input) and input[index].isalpha():
                index += 1
            string = input[start:index]
            ttype = (
                TokenType.BuiltinFunc if string in BUILTIN_FUNCS else TokenType.Ident
            )
            tokens.append(
                Token(
                    ttype=ttype,
                    value=string,
                    position=Position(path=path, line=line, row=row),
                )
            )
            row += len(string)
        elif ch.isnumeric() or ch == "-":
            start = index
            index += 1
            while index < len(input) and input[index].isnumeric():
                index += 1
            if input[index].isspace() or input[index] in SEPERATORS:
                num_str = input[start:index]
                tokens.append(
                    Token(
                        ttype=TokenType.Integer,
                        value=num_str,
                        position=Position(path=path, line=line, row=row),
                    )
                )
                row += len(num_str)
            else:
                eprint(f"{input[index]} is not allowed in numbers.")
                sys.exit(1)
        elif ch == '"':
            start = index
            index += 1
            while index < len(input) and input[index] != "\n" and input[index] != '"':
                index += 1

            if input[index] == '"':
                string = input[start + 1 : index]
                tokens.append(
                    Token(
                        ttype=TokenType.String,
                        value=string,
                        position=Position(path=path, line=line, row=row),
                    )
                )
                row += len(string) + 2  # 2 for " => "<string>"
            elif index >= len(input):
                eprint(
                    f'ERROR: {path}:{line}:{row}: expected " to end string but got EOF.'
                )
                sys.exit(1)
            elif input[index - 1] == "\n":
                eprint(f"ERROR: {path}:{line}:{row}: unterminated string literal")
                sys.exit(1)
            else:
                eprint(f"dont know what happend")
                sys.exit(1)
            index += 1
        elif ch == "(":
            tokens.append(
                Token(
                    ttype=TokenType.Lparen,
                    value="(",
                    position=Position(path=path, line=line, row=row),
                )
            )
            index += 1
            row += 1
        elif ch == ")":
            tokens.append(
                Token(
                    ttype=TokenType.Rparen,
                    value=")",
                    position=Position(path=path, line=line, row=row),
                )
            )
            index += 1
            row += 1
        elif ch == "=":
            tokens.append(
                Token(
                    ttype=TokenType.Assign,
                    value="=",
                    position=Position(path=path, line=line, row=row),
                )
            )
            index += 1
            row += 1
        else:
            eprint(red(f"skipping unprocessable token: {input[index]} at {index=}"))
            index += 1
            row += 1
    return tokens


def dump_tokens(tokens: list[Token]) -> None:
    for tok in tokens:
        print(tok)
