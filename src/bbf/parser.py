from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum, auto
import sys
from bbf.tokens import Token, TokenType
from bbf.utils import eprint


class ASTType(StrEnum):
    Program = auto()
    FunctionCall = auto()

    Integer = auto()
    String = auto()


@dataclass
class ASTNode:
    ttype: ASTType
    value: str
    children: list[ASTNode] = field(default_factory=list)


def parse(tokens: list[Token]) -> ASTNode:
    root = ASTNode(ttype=ASTType.Program, value="")
    index = 0
    while index < len(tokens):
        tok = tokens[index]
        if tok.ttype == TokenType.BuiltinFunc:
            node = ASTNode(ttype=ASTType.FunctionCall, value=tok.value)
            index += 1
            if index >= len(tokens):
                eprint(f"Expected '(' for function call '{node.value}', but got EOF.")
                sys.exit(1)
            if tokens[index].ttype != TokenType.Lparen:
                eprint(
                    f"Expected '(' for function root '{node.value}', but got {tokens[index].ttype.value}."
                )
                sys.exit(1)

            index += 1
            if index >= len(tokens):
                eprint(
                    f"Expected 'Integer' for function root '{node.value}', but got EOF."
                )
                sys.exit(1)

            while index < len(tokens) and tokens[index].ttype != TokenType.Rparen:
                t = tokens[index]
                if t.ttype == TokenType.Integer:
                    node.children.append(ASTNode(ttype=ASTType.Integer, value=t.value))
                elif t.ttype == TokenType.String:
                    node.children.append(ASTNode(ttype=ASTType.String, value=t.value))
                else:
                    eprint(
                        f"ERROR: unexpected token {t.ttype} for function call {node.value}"
                    )
                    sys.exit(1)
                index += 1
            if index >= len(tokens):
                eprint(f"ERROR: expected ')', but got EOF")
                sys.exit(1)
            elif tokens[index].ttype == TokenType.Rparen:
                index += 1
            else:
                eprint(f"ERROR: expected ')', but got {tokens[index]}")
                sys.exit(1)
            root.children.append(node)
        else:
            # eprint(f"skipping parsing of {tok!r}")
            index += 1
    return root
