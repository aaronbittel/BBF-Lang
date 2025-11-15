from __future__ import annotations

from bbf.lexer import Token, TokenType
from bbf.nodes.expr import (
    Argv,
    Binary,
    Expr,
    FnCall,
    Grouping,
    Identifier,
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
    Range,
    Stmt,
)
from bbf.nodes.toplevel import TopLevel, TopLevelStmt


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

    def parse_program(self) -> ProgTopLevelStmt:
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
        self.consume(TokenType.Minus, "Expected `-` in function definition")
        self.consume(TokenType.Greater, "Expected `>` in function definition")
        return_token = self.parse_fnreturn()
        self.consume(TokenType.Do, "Expected `do` in function definition")
        block = self.parse_block()
        return FnDef(name, args, return_token, block)

    def parse_return_stmt(self) -> ReturnStmt:
        # TODO: add empty return: First check if next token is a valid beginning of a
        # expression
        self.consume(TokenType.Return, "Expected `return` for return statement")
        # current = self.index
        try:
            expr = self.expr()
            return ReturnStmt(expr)
        except ParserError:
            print("[INFO] return statement without expr ?")
        return ReturnStmt()

    def parse_stmt(self) -> Stmt:
        if self.check(TokenType.If):
            return self.parse_if()
        if self.check(TokenType.For):
            return self.parse_for()
        if self.check(TokenType.Do):
            return self.parse_do_block()
        if self.check(TokenType.Identifier) and self.check(TokenType.Colon, offset=1):
            return self.parse_declaration()
        if self.check(TokenType.Identifier) and self.check(TokenType.Equal, offset=1):
            return self.parse_assignment()
        if self.check(TokenType.Return):
            return self.parse_return_stmt()
        return self.parse_expr_stmt()

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
        if not self.match(TokenType.Int, TokenType.String, TokenType.Void):
            raise ParserExpectError(
                self.peek(),
                "Expected `VarType` for function argument definition",
                TokenType.Int,
                TokenType.String,
                TokenType.Void,
            )
        vartype = self.previous()
        return Param(name, vartype)

    def parse_fnreturn(self) -> Token:
        if self.match(TokenType.Int, TokenType.String, TokenType.Void):
            return self.previous()
        raise ParserExpectError(
            self.peek(),
            "Expected `VarType` for function return type declaration",
            TokenType.Int,
            TokenType.String,
            TokenType.Void,
        )

    def parse_block(self) -> Block:
        block = Block()
        while not self.match(TokenType.End):
            block.add(self.parse_stmt())
        return block

    def parse_declaration(self) -> Declaration:
        name = self.consume(TokenType.Identifier, "Expected identifier in declaration")
        self.consume(TokenType.Colon, "Expected `:` in declaration for type")
        if not self.match(TokenType.Int, TokenType.String, TokenType.Void):
            raise ParserError(
                token=self.peek(),
                msg="No type annotation provided",
            )
        ttype = self.previous()
        self.consume(TokenType.Equal, "Expected `=` in declaration")
        expr = self.expr()
        return Declaration(name, ttype, expr)

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
        return self.equality()

    def equality(self) -> Expr:
        expr = self.comparison()
        while self.match(TokenType.BangEqual, TokenType.EqualEqual):
            operator = self.previous()
            right = self.comparison()
            expr = Binary(expr, operator, right)
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
            expr = Binary(expr, operator, right)
        return expr

    def term(self) -> Expr:
        expr = self.factor()
        while self.match(TokenType.Minus, TokenType.Plus):
            operator = self.previous()
            right = self.factor()
            expr = Binary(expr, operator, right)
        return expr

    def factor(self) -> Expr:
        expr = self.unary()
        while self.match(TokenType.Slash, TokenType.Star, TokenType.Percent):
            operator = self.previous()
            right = self.unary()
            expr = Binary(expr, operator, right)
        return expr

    def unary(self) -> Expr:
        if self.match(TokenType.Minus):
            operator = self.previous()
            right = self.unary()
            return Unary(operator, right)
        if self.match(TokenType.Plus):
            operator = self.previous()
            right = self.unary()
            return Unary(operator, right)
        if self.match(TokenType.Not):
            operator = self.previous()
            right = self.unary()
            return Unary(operator, right)
        return self.primary()

    def primary(self) -> Expr:
        if self.check(TokenType.IntegerLit):
            return IntegerLit(
                self.consume(TokenType.IntegerLit, msg="Expected `IntegerLit`")
            )
        if self.check(TokenType.Identifier) and self.peek().value == "argv":
            return self.argv()
        if self.check(TokenType.Identifier) and self.check(
            TokenType.OpenParen, offset=1
        ):
            return self.fn_call()
        if self.check(TokenType.Identifier):
            return Identifier(
                self.consume(TokenType.Identifier, "Expected `Identifier`")
            )
        if self.check(TokenType.OpenParen):
            self.consume(TokenType.OpenParen, "Expected `(` in expression")
            expr = self.expr()
            self.consume(TokenType.CloseParen, "Expected ')' after expression.")
            return Grouping(expr)
        if self.check(TokenType.StringLit):
            return StringLit(
                self.consume(TokenType.StringLit, "Expected `StringLiteral`")
            )
        token = self.peek()
        raise ParserError(token, f"Unknown statement beginning with `{token.value}`")

    def parse_function_call(self) -> FnCall:
        return self.fn_call()

    def fn_call(self) -> FnCall:
        name = self.consume(TokenType.Identifier, "Expected `name` for function call")
        self.consume(TokenType.OpenParen, "Expected `(` for function call")
        args_list: list[Expr] = []
        if not self.check(TokenType.CloseParen):
            args_list = self.args_list()
        self.consume(TokenType.CloseParen, "Expected `)` for function call")
        return FnCall(name, args_list)

    def args_list(self) -> list[Expr]:
        args: list[Expr] = [self.expr()]
        while self.match(TokenType.Comma):
            args.append(self.expr())
        return args

    def argv(self) -> Expr:
        self.consume(TokenType.Identifier, "Expected `argv`")
        self.consume(TokenType.OpenBracket, "Expected `[` in argv access")
        expr = self.expr()
        self.consume(TokenType.CloseBracket, "Expected `]` in argv access")
        return Argv(expr)

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
