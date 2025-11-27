from __future__ import annotations

from bbf.nodes.expr import (
    Argv,
    ArrayLiteral,
    Binary,
    BoolFalse,
    BoolTrue,
    Expr,
    FnCall,
    Grouping,
    Identifier,
    Indexing,
    IntegerLit,
    StringLit,
    Unary,
)
from bbf.nodes.program import ProgTopLevelStmt
from bbf.nodes.stmt import (
    Assignment,
    Block,
    Declaration,
    DoBlock,
    ElifStmt,
    ExprStmt,
    ForStmt,
    IfStmt,
    IndexAssign,
    Range,
    ReturnStmt,
    Stmt,
)
from bbf.nodes.toplevel import FnDef, Param, TopLevel, TopLevelStmt
from bbf.span import Span
from bbf.token import Token, TokenType
from bbf.utils import darkgray
from bbf.varinfo import ArrayType, SliceType, VarType, VoidType


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
        return f"ERROR: {self.token.position} Expected `{expected_str}`, but got `{self.token.value}`: {self.msg}"


# TODO: Maybe keep scope stack [If-For-...] to give better error message when coming
# across an unexpected token in parse_stmt
class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.index = 0

    def parse_prog(self) -> ProgTopLevelStmt:
        stmts: list[TopLevel] = []
        while not self.is_eof():
            stmts.append(self.parse_toplevel_stmt())
        return ProgTopLevelStmt(stmts)

    def parse_toplevel_stmt(self) -> TopLevel:
        if self.check(TokenType.Fn):
            return self.parse_fndef()
        return TopLevelStmt(self.parse_stmt())

    def parse_fndef(self) -> FnDef:
        self.consume(TokenType.Fn, "Expected `fn` in function definition")
        name = self.consume(
            TokenType.Identifier, "Expected `identifier` in function definition"
        )
        self.consume(TokenType.OpenParen, "Expected `(` in function definition")
        args: list[Param] = []
        if not self.check(TokenType.CloseParen):
            args = self.fndef_params()
        self.consume(TokenType.CloseParen, "Expected `)` in function definition")
        return_type = self.parse_fnreturn()
        self.consume(TokenType.Do, "Expected `do` to end function definition")
        block = self.parse_block()
        return FnDef(name, args, return_type, block)

    def parse_return_stmt(self) -> ReturnStmt:
        ret_token = self.consume(
            TokenType.Return, "Expected `return` for return statement"
        )
        try:
            expr = self.expr()
            return ReturnStmt(ret_token, expr)
        except ParserError:
            print(
                darkgray(
                    f"[INFO] {ret_token.position}: `return` statement without expr ?"
                )
            )
        return ReturnStmt(ret_token)

    def parse_stmt(self) -> Stmt:
        if self.check(TokenType.If):
            return self.parse_if()
        if self.check(TokenType.For):
            return self.parse_for()
        if self.check(TokenType.Do):
            return self.parse_do_block()
        if self.check(TokenType.Identifier):
            if self.check(TokenType.Colon, offset=1):
                return self.parse_declaration()
            if self.check(TokenType.Equal, offset=1):
                return self.parse_assignment()
            if self.check(TokenType.OpenBracket, offset=1):
                return self.parse_index_assign()
        if self.check(TokenType.Return):
            return self.parse_return_stmt()

        if self.check(TokenType.Colon, offset=1):
            raise ParserError(self.peek(), f"Cannot declare expr `{self.peek().value}`")
        if self.check(TokenType.Equal, offset=1):
            raise ParserError(
                self.peek(), f"Cannot assign to expr `{self.peek().value}`"
            )

        return self.parse_expr_stmt()

    def parse_index_assign(self) -> IndexAssign:
        name = self.consume(
            TokenType.Identifier, "Expected `Identifier` in array assignment"
        )
        self.consume(TokenType.OpenBracket, "Expected `[` in array assignment")
        index = self.expr()
        self.consume(TokenType.CloseBracket, "Expected `[` in array assignment")
        self.consume(TokenType.Equal, "Expected `=` in array assignment")
        expr = self.expr()
        return IndexAssign(name, index, expr)

    def parse_expr_stmt(self) -> ExprStmt:
        return ExprStmt(self.expr())

    def fndef_params(self) -> list[Param]:
        args = [self.fndef_param()]
        while self.match(TokenType.Comma):
            args.append(self.fndef_param())
        return args

    def fndef_param(self) -> Param:
        name = self.consume(
            TokenType.Identifier,
            "Expected `identifier` for function argument definition",
        )
        self.consume(TokenType.Colon, "Expected `:` in function argument definition")
        vartype = self.parse_vartype()
        return Param(name, vartype)

    def parse_fnreturn(self) -> VarType:
        if not (
            self.check(TokenType.Minus) and self.check(TokenType.Greater, offset=1)
        ):
            return VoidType

        self.advance()  # "-"
        self.advance()  # ">"
        return self.parse_vartype()

    def parse_block(self) -> Block:
        block = Block()
        while not self.match(TokenType.End):
            block.add(self.parse_stmt())
        return block

    def parse_declaration(self) -> Declaration:
        name = self.consume(TokenType.Identifier, "Expected identifier in declaration")
        self.consume(TokenType.Colon, "Expected `:` in declaration for type")
        vartype = self.parse_vartype()
        self.consume(TokenType.Equal, "Expected `=` in declaration")
        expr = self.expr()
        return Declaration(name, vartype, expr)

    def parse_vartype(self) -> VarType:
        if self.match(TokenType.OpenBracket):
            try:
                vartype = VarType.from_token(self.advance())
            except ValueError:
                raise ParserError(
                    self.peek(), f"`{self.peek()}` is not a valid VarType."
                )
            self.consume(TokenType.CloseBracket, "Expected `]` for slice type.")
            return SliceType(vartype)
        if not self.match(
            TokenType.Int, TokenType.String, TokenType.Void, TokenType.Bool
        ):
            raise ParserError(
                token=self.peek(),
                msg=f"Expected type annotation, but got `{self.peek().value}`",
            )
        try:
            vartype = VarType.from_token(self.previous())
        except ValueError:
            raise ParserError(self.peek(), f"`{self.peek()}` is not a valid VarType.")
        if self.match(TokenType.OpenBracket):
            length_token = self.consume(
                TokenType.IntegerLit, "Expected `IntegerLit` for array length"
            )
            try:
                length = int(length_token.value)
            except ValueError:
                raise ParserError(
                    length_token,
                    f"Expected `IntegerLit` for length of array, but got `{length_token.value}`",
                )
            self.consume(TokenType.CloseBracket, "Expected `]` for array declaration")
            vartype = ArrayType(vartype, length)
        return vartype

    def parse_assignment(self) -> Assignment:
        name = self.consume(TokenType.Identifier, "Expected identifier in assign")
        self.consume(TokenType.Equal, "Expected `=` in assign")
        expr = self.expr()
        return Assignment(name, expr)

    def parse_if(self) -> Stmt:
        self.consume(TokenType.If, "Expected `if` in if-statement")
        condition = self.expr()
        self.consume(TokenType.Then, "Expected `then` after if-condition")
        if_block = Block()
        while not self.match(TokenType.End, TokenType.Else, TokenType.Elif):
            s = self.parse_stmt()
            if_block.add(s)
        elif_branches: list[ElifStmt] = []
        if self.previous().ttype == TokenType.Elif:
            while True:
                elif_condition = self.expr()
                self.consume(TokenType.Then, "Expected `then` after elif-condition")
                elif_block = Block()
                while not self.match(TokenType.End, TokenType.Else, TokenType.Elif):
                    elif_block.add(self.parse_stmt())
                elif_branches.append(ElifStmt(elif_condition, elif_block))
                if self.previous().ttype != TokenType.Elif:
                    break
        if self.previous().ttype == TokenType.Else:
            else_block = Block()
            while not self.check(TokenType.End):
                else_block.add(self.parse_stmt())
            self.consume(TokenType.End, "Expected `end` after if-statement")
            return IfStmt(condition, if_block, elif_branches, else_block)
        if self.previous().ttype == TokenType.End:
            return IfStmt(condition, if_block, elif_branches)
        raise ParserError(
            token=self.previous(),
            msg="Expected one of `end`, `else` or `elif` keywords",
        )

    def parse_for(self) -> ForStmt:
        self.consume(TokenType.For, "Expected `for` in for loop")
        loop_ident = self.consume(
            TokenType.Identifier, "Expected `Identifier` in for loop"
        )
        self.consume(TokenType.In, "Expected `in` in for loop")
        range_expr = self.range_expr()
        block = self.block()
        return ForStmt(loop_ident, range_expr, block)

    def range_expr(self) -> Range:
        start = self.expr()
        self.consume(TokenType.Dot, "Expected `.` in range expression")
        self.consume(TokenType.Dot, "Expected `.` in range expression")
        inclusive = False
        if self.check(TokenType.Equal):
            self.advance()
            inclusive = True
        stop = self.expr()
        return Range(start, stop, inclusive)

    def parse_do_block(self) -> DoBlock:
        return DoBlock(self.block())

    def block(self) -> Block:
        self.consume(TokenType.Do, "Expected `do` in scope statement")
        block = Block()
        while not self.check(TokenType.End):
            block.add(self.parse_stmt())
        self.consume(TokenType.End, "Expected `end` to end scope statement")
        return block

    def expr(self) -> Expr:
        return self.bool_expr()

    def bool_expr(self) -> Expr:
        expr = self.or_expr()
        while self.match(TokenType.Or):
            operator = self.previous()
            right = self.or_expr()
            expr = Binary(
                expr, operator, right, span=Span(expr.span.start, right.span.end)
            )
        return expr

    def or_expr(self) -> Expr:
        expr = self.and_expr()
        while self.match(TokenType.And):
            operator = self.previous()
            right = self.and_expr()
            expr = Binary(
                expr, operator, right, span=Span(expr.span.start, right.span.end)
            )
        return expr

    def and_expr(self) -> Expr:
        return self.equality()

    def equality(self) -> Expr:
        expr = self.comparison()
        while self.match(TokenType.BangEqual, TokenType.EqualEqual):
            operator = self.previous()
            right = self.comparison()
            expr = Binary(
                expr, operator, right, span=Span(expr.span.start, right.span.end)
            )
        return expr

    def comparison(self) -> Expr:
        expr = self.term()
        while self.match(
            TokenType.Greater,
            TokenType.GreaterEqual,
            TokenType.Less,
            TokenType.LessEqual,
        ):
            operator = self.previous()
            right = self.term()
            expr = Binary(
                expr, operator, right, span=Span(expr.span.start, right.span.end)
            )
        return expr

    def term(self) -> Expr:
        expr = self.factor()
        while self.match(TokenType.Minus, TokenType.Plus):
            operator = self.previous()
            right = self.factor()
            expr = Binary(
                expr, operator, right, span=Span(expr.span.start, right.span.end)
            )
        return expr

    def factor(self) -> Expr:
        expr = self.unary()
        while self.match(TokenType.Slash, TokenType.Star, TokenType.Percent):
            operator = self.previous()
            right = self.unary()
            expr = Binary(
                expr, operator, right, span=Span(expr.span.start, right.span.end)
            )
        return expr

    def unary(self) -> Expr:
        if self.match(TokenType.Minus, TokenType.Plus, TokenType.Not):
            operator = self.previous()
            right = self.unary()
            return Unary(operator, right, span=Span(operator.position, right.span.end))
        return self.primary()

    def primary(self) -> Expr:
        if self.match(TokenType.IntegerLit):
            token = self.previous()
            return IntegerLit(token, span=Span.from_token(token))
        if self.check(TokenType.Identifier):
            if self.peek().value == "argv":
                return self.argv()
            if self.check(TokenType.OpenParen, offset=1):
                return self.fn_call()
            if self.check(TokenType.OpenBracket, offset=1):
                return self.indexing()
            token = self.advance()
            return Identifier(token, span=Span.from_token(token))
        if self.check(TokenType.OpenParen):
            start = self.consume(TokenType.OpenParen, "Expected `(` in expression")
            expr = self.expr()
            end = self.consume(TokenType.CloseParen, "Expected ')' after expression.")
            return Grouping(expr, span=Span(start.position, end.position))
        if self.match(TokenType.StringLit):
            token = self.previous()
            return StringLit(token, span=Span.from_token(token))
        if self.match(TokenType.BoolTrue):
            token = self.previous()
            return BoolTrue(token, span=Span.from_token(token))
        if self.match(TokenType.BoolFalse):
            token = self.previous()
            return BoolFalse(token, span=Span.from_token(token))
        if self.match(TokenType.OpenBracket):
            start = self.previous()
            args: list[Expr] = []
            if not self.check(TokenType.CloseBracket):
                args = self.arguments()
            end = self.consume(
                TokenType.CloseBracket, "Expected `]` to close ArrayLiteral"
            )
            return ArrayLiteral(args, span=Span(start.position, end.position))
        token = self.peek()
        if token.ttype == TokenType.Colon:
            msg = (
                f"Did you try to declare `{self.previous().value}` as a variable name?"
            )
        else:
            msg = f"Unknown statement beginning with `{token.value}`"
        raise ParserError(token, msg)

    def indexing(self) -> Indexing:
        name = self.consume(
            TokenType.Identifier, "Expected `Identifier` for array access"
        )
        self.consume(TokenType.OpenBracket, "Expected `[` for array access")
        expr = self.expr()
        end = self.consume(TokenType.CloseBracket, "Expected `]` for array access")
        return Indexing(name, expr, span=Span(name.position, end.position))

    def parse_function_call(self) -> FnCall:
        return self.fn_call()

    def fn_call(self) -> FnCall:
        name = self.consume(TokenType.Identifier, "Expected `name` for function call")
        self.consume(TokenType.OpenParen, "Expected `(` for function call")
        args_list: list[Expr] = []
        if not self.check(TokenType.CloseParen):
            args_list = self.arguments()
        end = self.consume(TokenType.CloseParen, "Expected `)` for function call")
        return FnCall(name, args_list, span=Span(name.position, end.position))

    def arguments(self) -> list[Expr]:
        args: list[Expr] = [self.expr()]
        while self.match(TokenType.Comma):
            args.append(self.expr())
        return args

    def argv(self) -> Expr:
        start = self.consume(TokenType.Identifier, "Expected `argv`")
        self.consume(TokenType.OpenBracket, "Expected `[` in argv access")
        expr = self.expr()
        end = self.consume(TokenType.CloseBracket, "Expected `]` in argv access")
        return Argv(span=Span(start.position, end.position), expr=expr)

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
