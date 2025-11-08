from __future__ import annotations

import sys
from dataclasses import dataclass, field

from bbf.lexer import Token, TokenType
from bbf.symbol_table import VarType
from bbf.utils import eprint


class ParserExpectError(Exception):
    def __init__(self, token: Token, expected: TokenType, msg: str) -> None:
        self.token = token
        self.expected = expected
        self.msg = msg

    def __str__(self) -> str:
        return f"ERROR: {self.token.position} Expected {self.expected}, but got {self.token}: {self.msg}"


class Parser:
    # TODO: input lexer instead?
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.index = 0

    def parse_program(self) -> NodeProgram:
        stmts: list[NodeStmt] = []
        while not self.is_eof():
            stmts.append(self.parse_stmt())
        return NodeProgram(stmts)

    def parse_stmt(self) -> NodeStmt:
        if self.check(TokenType.Exit):
            return self.parse_exit_expr()
        elif self.check(TokenType.Identifier):
            return self.parse_assign_stmt()
        elif self.check(TokenType.Print):
            return self.parse_print_stmt()
        else:
            token = self.peek()
            assert token is not None, "checke in `parse_program` that there is a token"
            eprint(f"ERROR: {token.position} unexpected token {token.value}")
            sys.exit(1)

    def parse_assign_stmt(self) -> NodeStmt:
        ident = self.consume(TokenType.Identifier, "Expected identifier in assign")
        self.consume(TokenType.Colon, "Expected `:` in assign for type")
        if self.match(TokenType.Int):
            ttype = VarType.Int
        elif self.match(TokenType.String):
            ttype = VarType.String
        else:
            # no type annotation provided
            # TODO: what is expected token type in this case?
            raise ParserExpectError(
                token=self.peek(),
                expected=TokenType.Illegal,
                msg="No type annotation provided",
            )
        self.consume(TokenType.Equal, "Expected `=` in assign")
        expr = self.expression()
        return NodeStmt(NodeStmtAssign(ident=ident, expr=expr, ttype=ttype))

    def parse_exit_expr(self) -> NodeStmt:
        self.consume(TokenType.Exit, "Expected `exit` call")
        self.consume(TokenType.OpenParen, "Expected `(` in `exit` call`")
        expr = self.expression()
        self.consume(TokenType.CloseParen, "Expected `)` in `exit` call")
        return NodeStmt(NodeStmtExit(expr))

    def parse_print_stmt(self) -> NodeStmt:
        self.consume(TokenType.Print, "Expected `print` call")
        self.consume(TokenType.OpenParen, "Expected `(` in print")
        expr = self.expression()
        self.consume(TokenType.CloseParen, "Expected `)` in print")
        return NodeStmt(NodeStmtPrint(expr))

    def expression(self) -> NodeExpr:
        expr = self.factor()
        while self.match(TokenType.Minus, TokenType.Plus):
            operator = self.previous()
            right = self.factor()
            expr = NodeExpr(NodeExprBinary(expr, operator, right))
        return expr

    def factor(self) -> NodeExpr:
        expr = self.unary()
        while self.match(TokenType.Slash, TokenType.Star, TokenType.Percent):
            operator = self.previous()
            right = self.unary()
            expr = NodeExpr(NodeExprBinary(expr, operator, right))
        return expr

    def unary(self) -> NodeExpr:
        if self.match(TokenType.Minus):
            operator = self.previous()
            right = self.unary()
            return NodeExpr(NodeExprUnary(operator, right))
        return self.primary()

    def primary(self) -> NodeExpr:
        if self.match(TokenType.IntegerLit):
            return NodeExpr(NodeExprIntLit(self.previous()))
        if self.match(TokenType.Identifier):
            return NodeExpr(NodeExprIdent(self.previous()))
        if self.match(TokenType.OpenParen):
            expr = self.expression()
            self.consume(TokenType.CloseParen, "Expect ')' after expression.")
            return NodeExpr(NodeExprGrouping(expr))
        if self.match(TokenType.StringLit):
            return NodeExpr(NodeExprStringLit(self.previous()))
        assert False, "unreachable"

    def peek(self, offset: int = 0) -> Token:
        return self.tokens[self.index + offset]

    def consume(self, ttype: TokenType, msg: str) -> Token:
        if self.check(ttype):
            return self.advance()
        raise ParserExpectError(token=self.peek(), expected=ttype, msg=msg)

    def advance(self) -> Token:
        if self.is_eof():
            return self.previous()
        self.index += 1
        return self.previous()

    def previous(self) -> Token:
        return self.tokens[self.index - 1]

    def check(self, ttype: TokenType, offset: int = 0) -> bool:
        if self.is_eof():
            return False
        return self.peek(offset).ttype == ttype

    def match(self, *types: TokenType) -> bool:
        for tt in types:
            if self.check(tt):
                self.advance()
                return True
        return False

    def is_eof(self) -> bool:
        return self.peek().ttype == TokenType.EOF


@dataclass
class NodeProgram:
    stmts: list[NodeStmt] = field(default_factory=list)

    def __str__(self) -> str:
        return "\n".join(str(s) for s in self.stmts)


@dataclass
class NodeStmt:
    stmt: NodeStmtExit | NodeStmtAssign | NodeStmtPrint

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
    ttype: VarType
    expr: NodeExpr

    def __str__(self) -> str:
        return f"assign[{self.ttype.value}]({self.ident.value} = {self.expr})"


@dataclass
class NodeStmtPrint:
    expr: NodeExpr

    def __str__(self) -> str:
        return f"print({self.expr})"


@dataclass
class NodeExpr:
    var: (
        NodeExprIntLit
        | NodeExprStringLit
        | NodeExprIdent
        | NodeExprBinary
        | NodeExprUnary
        | NodeExprGrouping
    )

    def __str__(self) -> str:
        return str(self.var)


@dataclass
class NodeExprIntLit:
    token: Token

    def __str__(self) -> str:
        return self.token.value


@dataclass
class NodeExprStringLit:
    token: Token

    def __str__(self) -> str:
        return f"{repr(self.token.value)}"


@dataclass
class NodeExprIdent:
    ident: Token

    def __str__(self) -> str:
        return self.ident.value


@dataclass
class NodeExprBinary:
    lhs: NodeExpr
    operator: Token
    rhs: NodeExpr

    def __str__(self) -> str:
        return f"( {self.lhs} {self.operator.value} {self.rhs} )"


@dataclass
class NodeExprUnary:
    operator: Token
    right: NodeExpr

    def __str__(self) -> str:
        return f"( {self.operator.value} {self.right} )"


@dataclass
class NodeExprGrouping:
    expr: NodeExpr

    def __str__(self) -> str:
        return f"( {self.expr} )"
