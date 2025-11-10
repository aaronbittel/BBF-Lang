from __future__ import annotations

from dataclasses import dataclass, field

from bbf.lexer import Token, TokenType
from bbf.symbol_table import VarType


class ParserError(Exception):
    def __init__(self, token: Token, msg: str) -> None:
        self.token = token
        self.msg = msg

    def __str__(self) -> str:
        return f"ERROR: {self.token.position}: {self.msg}"


class ParserExpectError(ParserError):
    def __init__(self, token: Token, msg: str, *expected: TokenType) -> None:
        self.token = token
        self.msg = msg
        self.expected = expected

    def __str__(self) -> str:
        expected_str = (
            str(self.expected[0])
            if len(self.expected) == 1
            else ", ".join(self.expected)
        )
        return f"ERROR: {self.token.position} Expected {expected_str}, but got {self.token}: {self.msg}"


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
            stmt = self.parse_exit_expr()
        elif self.check(TokenType.Identifier) and self.check(TokenType.Colon, offset=1):
            stmt = self.parse_decl_stmt()
        elif self.check(TokenType.Identifier) and self.check(TokenType.Equal, offset=1):
            stmt = self.parse_assign_stmt()
        elif self.check(TokenType.Print):
            stmt = self.parse_print_stmt()
        elif self.check(TokenType.If):
            stmt = self.parse_if_stmt()
        elif self.check(TokenType.For):
            stmt = self.parse_for_stmt()
        else:
            token = self.peek()
            raise ParserError(token=token, msg=f"unexpected token: {token.value}")
        return NodeStmt(stmt)

    def parse_decl_stmt(self) -> NodeStmtDecl:
        ident = self.consume(TokenType.Identifier, "Expected identifier in declaration")
        self.consume(TokenType.Colon, "Expected `:` in declaration for type")
        if self.match(TokenType.Int):
            ttype = VarType.Int
        elif self.match(TokenType.String):
            ttype = VarType.String
        else:
            raise ParserError(
                token=self.peek(),
                msg="No type annotation provided",
            )
        self.consume(TokenType.Equal, "Expected `=` in declaration")
        expr = self.expression()
        return NodeStmtDecl(ident=ident, expr=expr, ttype=ttype)

    def parse_assign_stmt(self) -> NodeStmtAssign:
        ident = self.consume(TokenType.Identifier, "Expected identifier in assign")
        self.consume(TokenType.Equal, "Expected `=` in assign")
        expr = self.expression()
        return NodeStmtAssign(ident=ident, expr=expr)

    def parse_exit_expr(self) -> NodeStmtExit:
        self.consume(TokenType.Exit, "Expected `exit` call")
        self.consume(TokenType.OpenParen, "Expected `(` in `exit` call`")
        expr = self.expression()
        self.consume(TokenType.CloseParen, "Expected `)` in `exit` call")
        return NodeStmtExit(expr)

    def parse_if_stmt(self) -> NodeStmtIf:
        # TODO: can I implement this without .previous() ?
        self.consume(TokenType.If, "Expected `if` in if-statement")
        condition = self.expression()
        self.consume(TokenType.Then, "Expected `then` after if-condition")
        if_stmts: list[NodeStmt] = []
        while not self.match(TokenType.End, TokenType.Else, TokenType.Elif):
            s = self.parse_stmt()
            if_stmts.append(s)
        elifs: list[NodeStmtElif] = []
        if self.previous().ttype == TokenType.Elif:
            while True:
                elif_condition = self.expression()
                self.consume(TokenType.Then, "Expected `then` after elif-condition")
                elif_stmts: list[NodeStmt] = []
                while not self.match(TokenType.End, TokenType.Else, TokenType.Elif):
                    s = self.parse_stmt()
                    elif_stmts.append(s)
                elifs.append(NodeStmtElif(condition=elif_condition, stmts=elif_stmts))
                if self.previous().ttype != TokenType.Elif:
                    break
        if self.previous().ttype == TokenType.Else:
            else_stmts: list[NodeStmt] = []
            while not self.check(TokenType.End):
                s = self.parse_stmt()
                else_stmts.append(s)
            self.consume(TokenType.End, "Expected `end` after if-statement")
            return NodeStmtIf(
                condition=condition,
                if_stmts=if_stmts,
                else_stmts=else_stmts,
                elifs=elifs,
            )
        if self.previous().ttype == TokenType.End:
            return NodeStmtIf(condition=condition, if_stmts=if_stmts, elifs=elifs)
        raise ParserError(
            token=self.previous(),
            msg="Expected one of `end`, `else` or `elif` keywords",
        )

    def parse_for_stmt(self) -> NodeStmtFor:
        self.consume(TokenType.For, "Expected `for` in for loop")
        ident = self.consume(TokenType.Identifier, "Expected `Identifier` in for loop")
        self.consume(TokenType.In, "Expected `in` in for loop")
        range_expr = self.range_expr()
        self.consume(TokenType.Do, "Expected `do` in for loop")
        stmts: list[NodeStmt] = []
        while not self.match(TokenType.End):
            stmts.append(self.parse_stmt())
        return NodeStmtFor(ident, range_expr, stmts)

    def range_expr(self) -> NodeExprRange:
        start = self.expression()
        self.consume(TokenType.Dot, "Expected `.` in range expression")
        self.consume(TokenType.Dot, "Expected `.` in range expression")
        inclusive = False
        if self.check(TokenType.Equal):
            self.advance()
            inclusive = True
        end = self.expression()
        return NodeExprRange(start, end, inclusive)

    def parse_print_stmt(self) -> NodeStmtPrint:
        self.consume(TokenType.Print, "Expected `print` call")
        self.consume(TokenType.OpenParen, "Expected `(` in print")
        expr = self.expression()
        self.consume(TokenType.CloseParen, "Expected `)` in print")
        return NodeStmtPrint(expr)

    def expression(self) -> NodeExpr:
        return self.equality()

    def equality(self) -> NodeExpr:
        expr = self.comparison()
        while self.match(TokenType.BangEqual, TokenType.EqualEqual):
            operator = self.previous()
            right = self.comparison()
            expr = NodeExpr(NodeExprBinary(expr, operator, right))
        return expr

    def comparison(self) -> NodeExpr:
        expr = self.term()
        while self.match(
            TokenType.Greater,
            TokenType.GreaterEqual,
            TokenType.Less,
            TokenType.LessEqual,
        ):
            operator = self.previous()
            right = self.term()
            expr = NodeExpr(NodeExprBinary(expr, operator, right))
        return expr

    def term(self) -> NodeExpr:
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
        if self.match(TokenType.Plus):
            operator = self.previous()
            right = self.unary()
            return NodeExpr(NodeExprUnary(operator, right))
        if self.match(TokenType.Not):
            operator = self.previous()
            right = self.unary()
            return NodeExpr(NodeExprUnary(operator, right))
        return self.primary()

    def primary(self) -> NodeExpr:
        if self.check(TokenType.IntegerLit):
            return NodeExpr(
                NodeExprIntLit(
                    self.consume(TokenType.IntegerLit, msg="Expected `IntegerLit`")
                )
            )
        if self.check(TokenType.Identifier) and self.peek().value == "argv":
            return NodeExpr(self.argv())
        if self.check(TokenType.Identifier):
            return NodeExpr(
                NodeExprIdent(
                    self.consume(TokenType.Identifier, "Expected `Identifier`")
                )
            )
        if self.check(TokenType.OpenParen):
            expr = self.expression()
            self.consume(TokenType.CloseParen, "Expect ')' after expression.")
            return NodeExpr(NodeExprGrouping(expr))
        if self.check(TokenType.StringLit):
            return NodeExpr(
                NodeExprStringLit(
                    self.consume(TokenType.StringLit, "Expected `StringLiteral`")
                )
            )
        assert False, f"unreachable: {self.peek()}"

    def argv(self) -> NodeExprArgv:
        self.consume(TokenType.Identifier, "Expected `argv`")
        self.consume(TokenType.OpenBracket, "Expected `[` in argv access")
        expr = self.expression()
        self.consume(TokenType.CloseBracket, "Expected `]` in argv access")
        return NodeExprArgv(expr)

    def peek(self, offset: int = 0) -> Token:
        return self.tokens[self.index + offset]

    def consume(self, ttype: TokenType, msg: str) -> Token:
        if self.check(ttype):
            return self.advance()
        raise ParserExpectError(self.peek(), msg, ttype)

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
    stmt: NodeStmtExit | NodeStmtDecl | NodeStmtPrint | NodeStmtIf | NodeStmtFor

    def __str__(self) -> str:
        return str(self.stmt)


@dataclass
class NodeStmtExit:
    expr: NodeExpr

    def __str__(self) -> str:
        return f"exit({self.expr})"


@dataclass
class NodeStmtDecl:
    ident: Token
    ttype: VarType
    expr: NodeExpr

    def __str__(self) -> str:
        return f"decl[{self.ttype.value}]({self.ident.value} = {self.expr})"


@dataclass
class NodeStmtAssign:
    ident: Token
    expr: NodeExpr

    def __str__(self) -> str:
        return f"assign({self.ident.value} = {self.expr})"


@dataclass
class NodeStmtElif:
    condition: NodeExpr
    stmts: list[NodeStmt]

    def __str__(self) -> str:
        out = f"elif {self.condition} then\n"
        for s in self.stmts:
            out += f"\t{s}\n"
        return out


@dataclass
class NodeStmtIf:
    condition: NodeExpr
    if_stmts: list[NodeStmt]
    elifs: list[NodeStmtElif] | None = None
    else_stmts: list[NodeStmt] | None = None

    def __str__(self) -> str:
        out = f"if {self.condition} then\n"
        for s in self.if_stmts:
            out += f"\t{s}\n"
        if self.elifs is not None:
            for el in self.elifs:
                out += str(el)
        if self.else_stmts is not None:
            out += "else\n"
            for s in self.else_stmts:
                out += f"\t{s}\n"
        out += "end"
        return out


@dataclass
class NodeExprRange:
    start: NodeExpr
    end: NodeExpr
    inclusive: bool

    def __str__(self) -> str:
        return f"{self.start}..{'=' if self.inclusive else ''}{self.end}"


@dataclass
class NodeStmtFor:
    loop_ident: Token
    range_expr: NodeExprRange
    stmts: list[NodeStmt]

    def __str__(self) -> str:
        out = f"for {self.loop_ident.value} in {self.range_expr} do\n"
        for s in self.stmts:
            out += f"\t{s}\n"
        out += "end"
        return out


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
        | NodeExprArgv
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
    expr: NodeExpr

    def __str__(self) -> str:
        return f"( {self.operator.value} {self.expr} )"


@dataclass
class NodeExprGrouping:
    expr: NodeExpr

    def __str__(self) -> str:
        return f"( {self.expr} )"


@dataclass
class NodeExprArgv:
    expr: NodeExpr

    def __str__(self) -> str:
        return f"argv[{self.expr}]"
