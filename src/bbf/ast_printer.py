import sys
from contextlib import contextmanager
from typing import Generator, TextIO

from bbf.nodes.expr import (
    Argv,
    ArrayLiteral,
    Binary,
    BoolFalse,
    BoolTrue,
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
    ExprStmt,
    ForStmt,
    IfStmt,
    IndexAssign,
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
            f"{param.name.value}: {param.vartype.name}" for param in fndef.params
        )
        self.write(
            f"fn {fndef.name.value}({params}) -> {fndef.ret_vartype.name} do", end="\n"
        )
        with self.indent_block():
            for stmt in fndef.body.stmts:
                stmt.accept(self)
        self.write("end", end="\n")

    def visit_forstmt(self, forstmt: ForStmt) -> None:
        self._ident(f"for {forstmt.loop_ident.value} in", end=" ")
        self._visit_range(forstmt.range_expr)
        self.write(" do", end="\n")
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
        self.write(" then", end="\n")
        self._visit_block(ifstmt.if_block)
        for elifstmt in ifstmt.elifs:
            self._ident("elif ", end="")
            elifstmt.condition.accept(self)
            self.write(" then", end="\n")
            self._visit_block(elifstmt.block)
        if len(ifstmt.else_block) > 0:
            self._ident("else", "\n")
            self._visit_block(ifstmt.else_block)
        self._ident("end", end="\n")

    def visit_returnstmt(self, returnstmt: ReturnStmt) -> None:
        self._ident("return", end=" ")
        if returnstmt.expr is not None:
            returnstmt.expr.accept(self)
        self.write(end="\n")

    def visit_exprstmt(self, exprstmt: ExprStmt) -> None:
        self._ident()
        exprstmt.expr.accept(self)
        self.write(end="\n")

    def visit_index_assign(self, index_assign: IndexAssign) -> None:
        self.write(index_assign.target.value)
        self.write("[")
        index_assign.index.accept(self)
        self.write("]")
        self.write(" = ")
        index_assign.value.accept(self)
        self.write(end="\n")

    def _visit_range(self, rangeexpr: Range) -> None:
        rangeexpr.start.accept(self)
        self.write("..")
        if rangeexpr.inclusive:
            self.write("=")
        rangeexpr.stop.accept(self)

    def _visit_block(self, block: Block) -> None:
        with self.indent_block():
            for stmt in block.stmts:
                stmt.accept(self)

    def visit_integerlit(self, intlit: IntegerLit) -> None:
        self.write(f"{intlit.token.value}")

    def visit_stringlit(self, strlit: StringLit) -> None:
        self.write(repr(strlit.token.value))

    def visit_identifier(self, ident: Identifier) -> None:
        self.write(ident.token.value)

    def visit_fncall(self, fncall: FnCall) -> None:
        self.write(f"{fncall.name.value}")
        self.write("( ")
        for i, arg in enumerate(fncall.args_list):
            arg.accept(self)
            if i + 1 < len(fncall.args_list):
                self.write(", ")
        self.write(" )")

    def visit_declaration(self, decl: Declaration) -> None:
        self._ident(f"{decl.name.value}: {decl.vartype.name} = ", end="")
        decl.expr.accept(self)
        self.write(end="\n")

    def visit_assignment(self, assign: Assignment) -> None:
        self._ident(f"{assign.name.value} = ", end="")
        assign.expr.accept(self)
        self.write(end="\n")

    def visit_binary(self, binary: Binary) -> None:
        self.write("( ")
        binary.lhs.accept(self)
        self.write(f" {binary.operator.value} ")
        binary.rhs.accept(self)
        self.write(" )")

    def visit_unary(self, unary: Unary) -> None:
        self.write(unary.operator.value)
        unary.expr.accept(self)

    def visit_grouping(self, grouping: Grouping) -> None:
        self.write("(")
        grouping.expr.accept(self)
        self.write(")")

    def visit_array_literal(self, array: ArrayLiteral) -> None:
        self.write("[", end=" ")
        for i, item in enumerate(array.items):
            if i != 0:
                self.write(", ")
            item.accept(self)
        self.write(" ]")

    def visit_indexing(self, subscript: Indexing) -> None:
        self.write(subscript.name.value)
        self.write("[")
        subscript.index.accept(self)
        self.write("]")

    def visit_argv(self, argv: Argv) -> None:
        self.write("argv")
        self.write("[")
        argv.expr.accept(self)
        self.write("]")

    def visit_booltrue(self, booltrue: BoolTrue) -> None:
        self.write("true")

    def visit_boolfalse(self, boolfalse: BoolFalse) -> None:
        self.write("false")

    @contextmanager
    def indent_block(self, level: int = 4) -> Generator[None, None, None]:
        self.indent += level
        yield
        self.indent -= level

    def _ident(self, text: str = "", end: str = "") -> None:
        self.write(f"{' ' * self.indent}{text}", end=end)

    def write(self, text: str = "", end: str = "") -> None:
        print(text, end=end, file=self.out)
