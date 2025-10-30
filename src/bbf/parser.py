from __future__ import annotations

from dataclasses import dataclass, field
import sys

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
        while (tok := self.peek()) and tok.ttype != TokenType.EOF:
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
            eprint(f"ERROR: {tok.position} unexpected token {tok.value}")
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
            token = self.consume()
            return NodeExpr(NodeExprIntLit(token))
        if self.check(TokenType.Identifier):
            token = self.consume()
            return NodeExpr(NodeExprIdent(token))
        # self.error(f"Expected expression, found {self.peek()}")
        token = self.peek()
        if token is None:
            eprint("ERROR: expected expression, found End of file")
        else:
            eprint(f"ERROR: {token.position} expected expression, found {token.value}")
        sys.exit(1)

    def peek(self, offset: int = 0) -> Token | None:
        if self.index + offset >= len(self.tokens):
            return None
        return self.tokens[self.index + offset]

    def consume(self) -> Token:
        """First check with peek() that there is a valid Token."""
        tok = self.peek()
        if tok is None:
            eprint("ERROR: unexpected end of input")
            sys.exit(1)
        self.index += 1
        return tok

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

    @property
    def current_token(self) -> Token:
        return self.tokens[self.index]


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
        return f"Assign({self.ident.value} = {self.expr})"


@dataclass
class NodeExpr:
    var: NodeExprIntLit | NodeExprIdent

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
