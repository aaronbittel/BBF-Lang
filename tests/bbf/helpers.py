from pathlib import Path

from bbf.lexer import Position, Token, TokenType
from bbf.parser import (
    NodeExpr,
    NodeExprIdent,
    NodeExprIntLit,
    NodeStmtDecl,
    NodeStmtExit,
)

TEST_PATH = Path("testing.bbf")

# TOKEN HELPERS


def p(line: int = 1, column: int = 1) -> Position:
    return Position(path=TEST_PATH, line=line, column=column)


def t(ttype: TokenType, value: str, line: int = 1, column: int = 1) -> Token:
    return Token(ttype=ttype, value=value, position=p(line, column))


def minus(line: int = 1, column: int = 1) -> Token:
    return t(ttype=TokenType.Minus, value="-", line=line, column=column)


def plus(line: int = 1, column: int = 1) -> Token:
    return t(ttype=TokenType.Plus, value="+", line=line, column=column)


def mult(line: int = 1, column: int = 1) -> Token:
    return t(ttype=TokenType.Star, value="*", line=line, column=column)


def div(line: int = 1, column: int = 1) -> Token:
    return t(ttype=TokenType.Slash, value="/", line=line, column=column)


def openp(line: int = 1, column: int = 1) -> Token:
    return t(ttype=TokenType.OpenParen, value="(", line=line, column=column)


def closep(line: int = 1, column: int = 1) -> Token:
    return t(ttype=TokenType.CloseParen, value=")", line=line, column=column)


def eof(line: int = 1, column: int = 1) -> Token:
    return t(ttype=TokenType.EOF, value="EOF", line=line, column=column)


def integer(value: int, line: int = 1, column: int = 1) -> Token:
    return t(ttype=TokenType.IntegerLit, value=str(value), line=line, column=column)


def string(value: str, line: int = 1, column: int = 1) -> Token:
    return t(ttype=TokenType.StringLit, value=value, line=line, column=column)


def ident(value: str, line: int = 1, column: int = 1) -> Token:
    return t(ttype=TokenType.Identifier, value=value, line=line, column=column)


def assign(line: int = 1, column: int = 1) -> Token:
    return t(ttype=TokenType.Equal, value="=", line=line, column=column)


def fn_exit(line: int = 1, column: int = 1) -> Token:
    return t(ttype=TokenType.Exit, value="exit", line=line, column=column)


# AST HELPERS


def int_lit(value: int):
    return NodeExpr(var=NodeExprIntLit(integer(value)))


def ident_expr(name: str):
    return NodeExpr(var=NodeExprIdent(ident(name)))


def assign_stmt(name: str, expr: NodeExpr):
    return NodeStmtDecl(ident=ident(name), expr=expr)


def exit_stmt(expr: NodeExpr):
    return NodeStmtExit(expr=expr)
