from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
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
    Declaration,
    DoBlock,
    ExprStmt,
    ForStmt,
    IfStmt,
    ReturnStmt,
)
from bbf.nodes.toplevel import FnDef, TopLevelStmt
from bbf.nodes.visitor import Visitor
from bbf.symbol_table import BUILTIN_FNS, FnInfo, VarType


@dataclass
class Scope:
    parent: Scope | None = None
    def_vars: dict[str, VarType] = field(default_factory=dict)

    def define(self, name: str, vartype: VarType) -> None:
        self.def_vars[name] = vartype

    def lookup(self, name: str) -> VarType | None:
        var = self.def_vars.get(name)
        if var is not None:
            return var
        cur = self.parent
        while cur is not None:
            var = cur.lookup(name)
            if var is not None:
                return var
            cur = cur.parent
        return None


class TypeCheckerError(Exception):
    pass


class TypeChecker(Visitor[VarType]):
    def __init__(self) -> None:
        self.defined_fns: dict[str, FnInfo] = {}
        for name, fninfo in BUILTIN_FNS.items():
            self.defined_fns[name] = fninfo
        self.scope = Scope()
        # TODO: Handle globals better
        self.scope.define("argc", VarType.Int)

    def visit_progtoplevelstmt(self, progtoplevelstmt: ProgTopLevelStmt) -> VarType:
        for stmt in progtoplevelstmt.stmts:
            stmt.accept(self)
        return VarType.Void

    def visit_toplevelstmt(self, toplevelstmt: TopLevelStmt) -> VarType:
        toplevelstmt.stmt.accept(self)
        return VarType.Void

    def visit_fndef(self, fndef: FnDef) -> VarType:
        if fndef.name.value in self.defined_fns:
            raise TypeCheckerError(f"fn `{fndef.name.value}` is already defined.")
        fninfo = FnInfo.from_node(fndef)
        self.defined_fns[fndef.name.value] = fninfo
        with self.new_scope():
            for arg in fninfo.args:
                self.scope.define(arg.name, arg.vartype)
            for stmt in fndef.body:
                stmt.accept(self)
        return VarType.Void

    def visit_forstmt(self, forstmt: ForStmt) -> VarType:
        rangeexpr = forstmt.range_expr
        start_type = rangeexpr.start.accept(self)
        if start_type != VarType.Int:
            raise TypeCheckerError(
                f"for-loop start expression must be Int, but got `{start_type.name}`"
            )
        stop_type = rangeexpr.stop.accept(self)
        if stop_type != VarType.Int:
            raise TypeCheckerError(
                f"for-loop stop expression must be Int, but got `{stop_type.name}`"
            )

        with self.new_scope():
            # because start and end type are `Int`, loop_ident can also be defined
            # to be `Int`
            self.scope.define(forstmt.loop_ident.value, VarType.Int)
            for stmt in forstmt.block:
                stmt.accept(self)
        return VarType.Void

    @contextmanager
    def new_scope(self) -> Generator[None, None, None]:
        try:
            old_scope = self.scope
            self.scope = Scope(parent=old_scope)
            yield
        finally:
            self.scope = old_scope

    def visit_doblock(self, doblock: DoBlock) -> VarType:
        with self.new_scope():
            for stmt in doblock.block:
                stmt.accept(self)
        return VarType.Void

    def visit_ifstmt(self, ifstmt: IfStmt) -> VarType:
        cond_type = ifstmt.condition.accept(self)
        if cond_type != VarType.Int:
            raise TypeCheckerError(f"if condition must be `Int`, got {cond_type.name}")

        with self.new_scope():
            for stmt in ifstmt.if_block:
                stmt.accept(self)

        for elif_ in ifstmt.elifs:
            elif_cond_type = elif_.condition.accept(self)
            if elif_cond_type != VarType.Int:
                raise TypeCheckerError(
                    f"elif condition must be `Int`, got {elif_cond_type}"
                )
            with self.new_scope():
                for elifstmt in elif_.block:
                    elifstmt.accept(self)

        with self.new_scope():
            for elsestmt in ifstmt.else_block:
                elsestmt.accept(self)

        return VarType.Void

    def visit_returnstmt(self, returnstmt: ReturnStmt) -> VarType:
        if returnstmt.expr is None:
            return VarType.Void
        return returnstmt.expr.accept(self)

    def visit_exprstmt(self, exprstmt: ExprStmt) -> VarType:
        exprstmt.expr.accept(self)
        return VarType.Void

    def visit_integerlit(self, intlit: IntegerLit) -> VarType:
        return VarType.Int

    def visit_stringlit(self, strlit: StringLit) -> VarType:
        return VarType.String

    def visit_identifier(self, ident: Identifier) -> VarType:
        name = ident.token.value
        vartype = self.scope.lookup(name)
        if vartype is None:
            raise TypeCheckerError(
                f"ERROR: {ident.token.position}: `{name}` is not defined."
            )
        return vartype

    def visit_fncall(self, fncall: FnCall) -> VarType:
        # TODO: make it that I dont have to define the function before using it
        fnname = fncall.name.value
        fninfo = self.defined_fns.get(fnname)
        if fninfo is None:
            raise TypeCheckerError(f"Undefined function `{fnname}`")

        if len(fninfo.args) != len(fncall.args_list):
            raise TypeCheckerError(
                f"ERROR: {fncall.name.position}: "
                f"Function `{fnname}` expects {len(fninfo.args)} arguments, "
                f"but got {len(fncall.args_list)}"
            )

        for i, (fnarg, arg) in enumerate(zip(fninfo.args, fncall.args_list), start=1):
            got = arg.accept(self)
            expected = fnarg.vartype
            param_name = "" if fnname in BUILTIN_FNS else f" `{fnarg.name}`"
            if expected != got:
                raise TypeCheckerError(
                    f"ERROR: {fncall.name.position}: "
                    f"Type mismatch in call to `{fnname}`: "
                    f"expected `{expected.name}` for {i}. parameter{param_name}, "
                    f"but got `{got.name}`"
                )

        return fninfo.return_type

    def visit_declaration(self, decl: Declaration) -> VarType:
        self.scope.define(decl.name.value, decl.expr.accept(self))
        return VarType.Void

    def visit_assignment(self, assign: Assignment) -> VarType:
        name = assign.name.value
        got_type = assign.expr.accept(self)
        expected_type = self.scope.lookup(name)
        if expected_type is None:
            raise TypeCheckerError(
                f"ERROR at {assign.name.position}: "
                f"Cannot assign to `{name}` because it is not defined."
            )
        if expected_type != got_type:
            raise TypeCheckerError(
                f"ERROR at {assign.name.position}: "
                f"Type mismatch in assignment to `{name}`. "
                f"Expected: {expected_type}, but got: {got_type}"
            )
        return VarType.Void

    def visit_binary(self, binary: Binary) -> VarType:
        lhs_type = binary.lhs.accept(self)
        rhs_type = binary.rhs.accept(self)

        if lhs_type != rhs_type:
            raise TypeCheckerError(
                f"Type mismatch in binary expression: {lhs_type.name} {binary.operator.value} {rhs_type.name}"
            )

        if lhs_type == VarType.Int:
            return VarType.Int

        raise TypeCheckerError(
            f"Operator `{binary.operator.value}` is not supported between {lhs_type.name} and {rhs_type.name}"
        )

    def visit_unary(self, unary: Unary) -> VarType:
        expr_type = unary.expr.accept(self)
        if expr_type != VarType.Int:
            raise TypeCheckerError(
                f"Unary operator `{unary.operator.value}` is only allowed on Int, got {expr_type.name}"
            )
        return VarType.Int

    def visit_grouping(self, grouping: Grouping) -> VarType:
        return grouping.expr.accept(self)

    def visit_argv(self, argv: Argv) -> VarType:
        argv.expr.accept(self)
        return VarType.String
