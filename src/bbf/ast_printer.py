from contextlib import contextmanager
from typing import Generator

from bbf.nodes.expr import (
    Argv,
    Binary,
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
)
from bbf.nodes.toplevel import FnDef, TopLevelStmt
from bbf.nodes.visitor import Visitor


class ASTPrinter(Visitor):
    def __init__(self) -> None:
        self.indent = 0

    def visit_progtoplevelstmt(
        self, programtoplevelstatement: ProgTopLevelStmt
    ) -> None:
        for stmt in programtoplevelstatement.stmts:
            stmt.accept(self)

    def visit_toplevelstmt(self, toplevelstatement: TopLevelStmt) -> None:
        toplevelstatement.stmt.accept(self)

    def visit_fndef(self, functiondefinition: FnDef) -> None:
        params = ", ".join(
            f"{param.name.value}: {param.vartype.value}"
            for param in functiondefinition.params
        )
        print(
            f"fn {functiondefinition.name.value}({params}) -> {functiondefinition.return_type.value} do"
        )
        with self.indent_block():
            for stmt in functiondefinition.body.stmts:
                stmt.accept(self)
        print("end")

    def visit_forstmt(self, forstmt: ForStmt) -> None:
        self._ident(f"for {forstmt.loop_ident.value} in", end=" ")
        self._visit_range(forstmt.range_expr)
        print(" do")
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
        print(" then")
        self._visit_block(ifstmt.if_block)
        for elifstmt in ifstmt.elifs:
            self._ident("elif ", end="")
            elifstmt.condition.accept(self)
            print(" then")
            self._visit_block(elifstmt.block)
        if ifstmt.else_block:
            self._ident("else", "\n")
            self._visit_block(ifstmt.else_block)
        self._ident("end", end="\n")

    def visit_exprstmt(self, expressionstmt: ExprStmt) -> None:
        self._ident()
        expressionstmt.expr.accept(self)
        print()

    def _visit_range(self, rangeexpr: Range) -> None:
        rangeexpr.start.accept(self)
        print("..", end="")
        if rangeexpr.inclusive:
            print("=", end="")
        rangeexpr.stop.accept(self)

    def _visit_block(self, block: Block) -> None:
        with self.indent_block():
            for stmt in block.stmts:
                stmt.accept(self)

    def visit_integerlit(self, intlit: IntegerLit) -> None:
        print(f"{intlit.token.value}", end="")

    def visit_stringlit(self, strlit: StringLit) -> None:
        print(repr(strlit.token.value), end="")

    def visit_identifier(self, ident: Identifier) -> None:
        print(ident.token.value, end="")

    def visit_fncall(self, fncall: FnCall) -> None:
        print(f"{fncall.name.value}", end="")
        print("( ", end="")
        for i, arg in enumerate(fncall.args_list):
            arg.accept(self)
            if i + 1 < len(fncall.args_list):
                print(", ", end="")
        print(" )", end="")

    def visit_declaration(self, decl: Declaration) -> None:
        self._ident(f"{decl.name.value}: {decl.typetoken.value} = ", end="")
        decl.expr.accept(self)
        print()

    def visit_assignment(self, assign: Assignment) -> None:
        self._ident(f"{assign.name.value} = ", end="")
        assign.expr.accept(self)
        print()

    def visit_binary(self, binary: Binary) -> None:
        print("( ", end="")
        binary.lhs.accept(self)
        print(f" {binary.operator.value} ", end="")
        binary.rhs.accept(self)
        print(" )", end="")

    def visit_unary(self, unary: Unary) -> None:
        print(unary.operator.value, end="")
        unary.expr.accept(self)

    def visit_grouping(self, grouping: Grouping) -> None:
        print("(", end="")
        grouping.expr.accept(self)
        print(")", end="")

    def visit_argv(self, argv: Argv) -> None:
        print("argv", end="")
        print("[", end="")
        argv.expr.accept(self)
        print("]", end="")

    @contextmanager
    def indent_block(self, level: int = 4) -> Generator[None, None, None]:
        self.indent += level
        yield
        self.indent -= level

    def _ident(self, text: str = "", end: str = "") -> None:
        print(f"{' ' * self.indent}{text}", end=end)
