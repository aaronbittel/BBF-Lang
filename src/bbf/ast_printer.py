import sys
from contextlib import contextmanager
from typing import Generator, TextIO

from bbf.nodes.expr import (
    Argv,
    Binary,
    BoolFalse,
    BoolTrue,
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
    ExprStmt,
    ForStmt,
    IfStmt,
    Range,
    ReturnStmt,
)
from bbf.nodes.toplevel import FnDef, TopLevelStmt
from bbf.nodes.visitor import Visitor


class ASTPrinter(Visitor[None]):
    def __init__(self, out: TextIO = sys.stdout) -> None:
        self.out = out
        self.indent = 0

    def visit_progtoplevelstmt(self, progtoplevelstmt: ProgTopLevelStmt) -> None:
        for stmt in progtoplevelstmt.stmts:
            stmt.accept(self)

    def visit_toplevelstmt(self, toplevelstmt: TopLevelStmt) -> None:
        toplevelstmt.stmt.accept(self)

    def visit_fndef(self, fndef: FnDef) -> None:
        params = ", ".join(
            f"{param.name.value}: {param.ttype.value}" for param in fndef.params
        )
        print(
            f"fn {fndef.name.value}({params}) -> {fndef.ret_vartype.name} do",
            file=self.out,
        )
        with self.indent_block():
            for stmt in fndef.body.stmts:
                stmt.accept(self)
        print("end", file=self.out)

    def visit_forstmt(self, forstmt: ForStmt) -> None:
        self._ident(f"for {forstmt.loop_ident.value} in", end=" ")
        self._visit_range(forstmt.range_expr)
        print(" do", file=self.out)
        self._visit_block(forstmt.block)
        self._ident("end", end="\n")

    def visit_doblock(self, doblock: DoBlock) -> None:
        self._ident("do", end="\n")
        with self.indent_block():
            for stmt in doblock.block.stmts:
                stmt.accept(self)
        self._ident("end", end="\n")

    def visit_ifstmt(self, ifstmt: IfStmt) -> None:
        self._ident("if ", end="")
        ifstmt.condition.accept(self)
        print(" then", file=self.out)
        self._visit_block(ifstmt.if_block)
        for elifstmt in ifstmt.elifs:
            self._ident("elif ", end="")
            elifstmt.condition.accept(self)
            print(" then", file=self.out)
            self._visit_block(elifstmt.block)
        if len(ifstmt.else_block) > 0:
            self._ident("else", "\n")
            self._visit_block(ifstmt.else_block)
        self._ident("end", end="\n")

    def visit_returnstmt(self, returnstmt: ReturnStmt) -> None:
        self._ident("return", end=" ")
        if returnstmt.expr is not None:
            returnstmt.expr.accept(self)
        print(file=self.out)

    def visit_exprstmt(self, exprstmt: ExprStmt) -> None:
        self._ident()
        exprstmt.expr.accept(self)
        print(file=self.out)

    def _visit_range(self, rangeexpr: Range) -> None:
        rangeexpr.start.accept(self)
        print("..", end="", file=self.out)
        if rangeexpr.inclusive:
            print("=", end="", file=self.out)
        rangeexpr.stop.accept(self)

    def _visit_block(self, block: Block) -> None:
        with self.indent_block():
            for stmt in block.stmts:
                stmt.accept(self)

    def visit_integerlit(self, intlit: IntegerLit) -> None:
        print(f"{intlit.token.value}", end="", file=self.out)

    def visit_stringlit(self, strlit: StringLit) -> None:
        print(repr(strlit.token.value), end="", file=self.out)

    def visit_identifier(self, ident: Identifier) -> None:
        print(ident.token.value, end="", file=self.out)

    def visit_fncall(self, fncall: FnCall) -> None:
        print(f"{fncall.name.value}", end="", file=self.out)
        print("( ", end="", file=self.out)
        for i, arg in enumerate(fncall.args_list):
            arg.accept(self)
            if i + 1 < len(fncall.args_list):
                print(", ", end="", file=self.out)
        print(" )", end="", file=self.out)

    def visit_declaration(self, decl: Declaration) -> None:
        self._ident(f"{decl.name.value}: {decl.typetoken.value} = ", end="")
        decl.expr.accept(self)
        print(file=self.out)

    def visit_assignment(self, assign: Assignment) -> None:
        self._ident(f"{assign.name.value} = ", end="")
        assign.expr.accept(self)
        print(file=self.out)

    def visit_binary(self, binary: Binary) -> None:
        print("( ", end="", file=self.out)
        binary.lhs.accept(self)
        print(f" {binary.operator.value} ", end="", file=self.out)
        binary.rhs.accept(self)
        print(" )", end="", file=self.out)

    def visit_unary(self, unary: Unary) -> None:
        print(unary.operator.value, end="", file=self.out)
        unary.expr.accept(self)

    def visit_grouping(self, grouping: Grouping) -> None:
        print("(", end="", file=self.out)
        grouping.expr.accept(self)
        print(")", end="", file=self.out)

    def visit_argv(self, argv: Argv) -> None:
        print("argv", end="", file=self.out)
        print("[", end="", file=self.out)
        argv.expr.accept(self)
        print("]", end="", file=self.out)

    def visit_booltrue(self, booltrue: BoolTrue) -> None:
        print("true", end="", file=self.out)

    def visit_boolfalse(self, boolfalse: BoolFalse) -> None:
        print("false", end="", file=self.out)

    @contextmanager
    def indent_block(self, level: int = 4) -> Generator[None, None, None]:
        self.indent += level
        yield
        self.indent -= level

    def _ident(self, text: str = "", end: str = "") -> None:
        print(f"{' ' * self.indent}{text}", end=end, file=self.out)
