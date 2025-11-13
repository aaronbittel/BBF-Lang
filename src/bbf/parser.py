from __future__ import annotations

from dataclasses import dataclass

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


# TODO: Maybe keep scope stack [If-For-...] to give better error message when coming
# across an unexpected token in parse_stmt
class Parser:
    # TODO: input lexer instead?
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.index = 0

    def parse_program(self) -> NodeProgram:
        stmts: list[NodeStmt] = []
        while not self.is_eof():
            stmts.append(self.parse_stmt())
        return NodeProgram(NodeStmtScope(stmts))

    def parse_stmt(self) -> NodeStmt:
        if self.check(TokenType.Identifier) and self.check(TokenType.Colon, offset=1):
            stmt = self.parse_decl_stmt()
        elif self.check(TokenType.Identifier) and self.check(TokenType.Equal, offset=1):
            stmt = self.parse_assign_stmt()
        elif self.check(TokenType.If):
            stmt = self.parse_if_stmt()
        elif self.check(TokenType.For):
            stmt = self.parse_for_stmt()
        elif self.check(TokenType.Do):
            stmt = self.parse_scope_stmt()
        elif self.check(TokenType.Identifier) and self.check(
            TokenType.OpenParen, offset=1
        ):
            stmt = self.fn_call()
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

    def parse_if_stmt(self) -> NodeStmtIf:
        # TODO: can I implement this without .previous() ?
        self.consume(TokenType.If, "Expected `if` in if-statement")
        condition = self.expression()
        self.consume(TokenType.Then, "Expected `then` after if-condition")
        if_stmts: list[NodeStmt] = []
        while not self.match(TokenType.End, TokenType.Else, TokenType.Elif):
            s = self.parse_stmt()
            if_stmts.append(s)
        scope = NodeStmtScope(if_stmts)
        elifs: list[NodeStmtElif] = []
        if self.previous().ttype == TokenType.Elif:
            while True:
                elif_condition = self.expression()
                self.consume(TokenType.Then, "Expected `then` after elif-condition")
                elif_stmts: list[NodeStmt] = []
                while not self.match(TokenType.End, TokenType.Else, TokenType.Elif):
                    s = self.parse_stmt()
                    elif_stmts.append(s)
                elifs.append(
                    NodeStmtElif(
                        condition=elif_condition, scope=NodeStmtScope(elif_stmts)
                    )
                )
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
                scope=scope,
                else_scope=NodeStmtScope(else_stmts),
                elifs=elifs,
            )
        if self.previous().ttype == TokenType.End:
            return NodeStmtIf(condition=condition, scope=scope, elifs=elifs)
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
        return NodeStmtFor(ident, range_expr, scope=NodeStmtScope(stmts))

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

    def parse_scope_stmt(self) -> NodeStmtScope:
        self.consume(TokenType.Do, "Expected `do` in scope statement")
        stmts: list[NodeStmt] = []
        while not self.check(TokenType.End):
            stmts.append(self.parse_stmt())
        self.consume(TokenType.End, "Expected `end` to end scope statement")
        return NodeStmtScope(stmts)

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
        if self.check(TokenType.Identifier) and self.check(
            TokenType.OpenParen, offset=1
        ):
            return NodeExpr(self.fn_call())
        if self.check(TokenType.Identifier):
            return NodeExpr(
                NodeExprIdent(
                    self.consume(TokenType.Identifier, "Expected `Identifier`")
                )
            )
        if self.check(TokenType.OpenParen):
            self.consume(TokenType.OpenParen, "Expected `(` in expression")
            expr = self.expression()
            self.consume(TokenType.CloseParen, "Expected ')' after expression.")
            return NodeExpr(NodeExprGrouping(expr))
        if self.check(TokenType.StringLit):
            return NodeExpr(
                NodeExprStringLit(
                    self.consume(TokenType.StringLit, "Expected `StringLiteral`")
                )
            )
        assert False, f"unreachable: {self.peek()}"

    def fn_call(self) -> NodeExprFnCall:
        name = self.consume(TokenType.Identifier, "Expected `name` for function call")
        self.consume(TokenType.OpenParen, "Expected `(` for function call")
        args_list: list[NodeExpr] = []
        if not self.check(TokenType.CloseParen):
            args_list = self.args_list()
        self.consume(TokenType.CloseParen, "Expected `)` for function call")
        return NodeExprFnCall(name, args_list)

    def args_list(self) -> list[NodeExpr]:
        args: list[NodeExpr] = [self.expression()]
        while self.match(TokenType.Comma):
            args.append(self.expression())
        return args

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


# TODO: Remove string formatting from Nodes and implement some kind of Visitor that
# pretty prints the NodeProgram AST


@dataclass
class NodeProgram:
    scope: NodeStmtScope

    def __str__(self) -> str:
        return str(self.scope)


@dataclass
class NodeStmt:
    stmt: (
        NodeStmtDecl
        | NodeStmtIf
        | NodeStmtFor
        | NodeStmtAssign
        | NodeStmtScope
        | NodeExprFnCall
    )

    def __str__(self) -> str:
        return str(self.stmt)


@dataclass
class NodeStmtDecl:
    ident: Token
    ttype: VarType
    expr: NodeExpr

    def __str__(self) -> str:
        return f"decl[{self.ttype.name}]({self.ident.value} = {self.expr})"


@dataclass
class NodeStmtAssign:
    ident: Token
    expr: NodeExpr

    def __str__(self) -> str:
        return f"assign({self.ident.value} = {self.expr})"


@dataclass
class NodeStmtElif:
    condition: NodeExpr
    scope: NodeStmtScope

    def __str__(self) -> str:
        return f"elif {self.condition} then\n{self.scope}"


@dataclass
class NodeStmtIf:
    condition: NodeExpr
    scope: NodeStmtScope
    elifs: list[NodeStmtElif]
    else_scope: NodeStmtScope | None = None

    def __str__(self) -> str:
        out = f"if {self.condition} then\n"
        out += str(self.scope)
        if self.elifs is not None:
            for el in self.elifs:
                out += str(el)
        if self.else_scope is not None:
            out += "else\n\t{else_scope}\n"
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
    scope: NodeStmtScope

    def __str__(self) -> str:
        return f"for {self.loop_ident.value} in {self.range_expr} do{self.scope}\nend"


@dataclass
class NodeStmtScope:
    stmts: list[NodeStmt]

    def __str__(self) -> str:
        return f"Scoped({'\n\t'.join(str(stmt) for stmt in self.stmts)})"


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
        | NodeExprFnCall
    )

    def __str__(self) -> str:
        return str(self.var)


@dataclass
class NodeExprFnCall:
    name: Token
    args_list: list[NodeExpr]

    def __str__(self) -> str:
        return f"{self.name.value}({', '.join(str(e) for e in self.args_list)})"


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
    token: Token

    def __str__(self) -> str:
        return self.token.value


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
