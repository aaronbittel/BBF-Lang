from __future__ import annotations

import sys
from dataclasses import dataclass, field

from bbf.lexer import Position, Token, TokenType
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

    def parse_program(self) -> NodeProgram:
        stmts: list[NodeStmt] = []
        while (token := self.peek()) and token.ttype != TokenType.EOF:
            stmts.append(self.parse_stmt())
        return NodeProgram(stmts)

    def parse_stmt(self) -> NodeStmt:
        if self.check(TokenType.Exit) and self.check(TokenType.OpenParen, offset=1):
            return NodeStmt(self.parse_exit_expr())
        elif self.check(TokenType.Identifier) and self.check(
            TokenType.Assign, offset=1
        ):
            return NodeStmt(self.parse_assign_stmt())
        else:
            token = self.peek()
            assert token is not None, "checke in `parse_program` that there is a token"
            eprint(f"ERROR: {token.position} unexpected token {token.value}")
            sys.exit(1)

    def parse_assign_stmt(self) -> NodeStmtAssign:
        ident = self.expect(TokenType.Identifier)
        self.expect(TokenType.Assign)
        expr = self.parse_expr()
        return NodeStmtAssign(ident, expr)

    def parse_exit_expr(self) -> NodeStmtExit:
        self.expect(TokenType.Exit)
        self.expect(TokenType.OpenParen)
        expr = self.parse_expr()
        self.expect(TokenType.CloseParen)
        return NodeStmtExit(expr)

    def parse_expr(self) -> NodeExpr:
        if self.check(TokenType.Integer):
            left = NodeExpr(NodeExprIntLit(self.consume()))
        elif self.check(TokenType.Identifier):
            left = NodeExpr(NodeExprIdent(self.consume()))
        else:
            left = self.peek()
            if left is None:
                eprint("ERROR: expected expression, found End of file")
            else:
                eprint(
                    f"ERROR: {left.position} expected expression, found {left.value}"
                )
            sys.exit(1)

        if self.check(TokenType.Plus):
            self.consume()
            right = self.parse_expr()
            return NodeExpr(NodeExprAdd(lhs=left, rhs=right))

        return left

    def peek(self, offset: int = 0) -> Token | None:
        if self.index + offset >= len(self.tokens):
            return None
        return self.tokens[self.index + offset]

    def consume(self) -> Token:
        """First check with peek() that there is a valid Token."""
        token = self.peek()
        if token is None:
            eprint("ERROR: unexpected end of input")
            sys.exit(1)
        self.index += 1
        return token

    def check(self, ttype: TokenType, offset: int = 0) -> bool:
        token = self.peek(offset)
        return token is not None and token.ttype == ttype

    def expect(self, ttype: TokenType) -> Token:
        token = self.peek()
        if token is None or token.ttype != ttype:
            # self.error(f"Expected {token_type}, found {token}")
            eprint(f"Expected {ttype}, found {token.ttype if token else None}")
            sys.exit(1)
        return self.consume()


@dataclass
class NodeProgram:
    stmts: list[NodeStmt] = field(default_factory=list)

    def __str__(self) -> str:
        return "\n".join(str(s) for s in self.stmts)


@dataclass
class NodeStmt:
    stmt: NodeStmtExit | NodeStmtAssign

    def __str__(self) -> str:
        return str(self.stmt)


@dataclass
class NodeStmtExit:
    expr: NodeExpr

    def __str__(self) -> str:
        return f"exit({self.expr})"


@dataclass
class NodeStmtAssign:
    ident: Token
    expr: NodeExpr

    def __str__(self) -> str:
        return f"assign({self.ident.value} = {self.expr})"


@dataclass
class NodeExpr:
    var: NodeExprIntLit | NodeExprIdent | NodeExprAdd

    def __str__(self) -> str:
        return str(self.var)


@dataclass
class NodeExprIntLit:
    int_lit: Token

    def __str__(self) -> str:
        return self.int_lit.value


@dataclass
class NodeExprIdent:
    ident: Token

    def __str__(self) -> str:
        return self.ident.value


@dataclass
class NodeExprAdd:
    lhs: NodeExpr
    rhs: NodeExpr

    def __str__(self) -> str:
        return f"{self.lhs} + {self.rhs}"
