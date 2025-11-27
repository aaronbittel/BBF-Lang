from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Generator

from bbf.functions import BUILTIN_FNS, FnInfo
from bbf.lexer import TokenType
from bbf.nodes.expr import (
    Argv,
    ArrayLiteral,
    Binary,
    BoolFalse,
    BoolTrue,
    FnCall,
    Grouping,
    Identifier,
    IntegerLit,
    StringLit,
    Subscript,
    Unary,
)
from bbf.nodes.program import ProgTopLevelStmt
from bbf.nodes.stmt import (
    ArrayAssign,
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
from bbf.varinfo import (
    ArrayType,
    BoolType,
    IntType,
    SliceType,
    StringType,
    VarType,
    VoidType,
)


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
        self.defined_fns = deepcopy(BUILTIN_FNS)
        self.scope = Scope()
        self.expected_vartype: VarType | None = None
        # TODO: Handle globals better
        self.scope.define("argc", IntType)
        self.current_fninfo: FnInfo | None = None

    def visit_progtoplevelstmt(self, progtoplevelstmt: ProgTopLevelStmt) -> VarType:
        for stmt in progtoplevelstmt.stmts:
            stmt.accept(self)
        return VoidType

    def visit_toplevelstmt(self, toplevelstmt: TopLevelStmt) -> VarType:
        toplevelstmt.stmt.accept(self)
        return VoidType

    def visit_fndef(self, fndef: FnDef) -> VarType:
        if fndef.name.value in self.defined_fns:
            raise TypeCheckerError(
                f"ERROR: {fndef.name.position}: fn `{fndef.name.value}` is already defined."
            )
        fninfo = FnInfo.from_node(fndef)
        self.defined_fns[fndef.name.value] = fninfo
        with self.new_scope():
            for arg in fninfo.args:
                if arg.vartype == VoidType:
                    raise TypeCheckerError(
                        f"ERROR: {fndef.name.position}: `Void` is not allowed as function parameter type"
                    )
                self.scope.define(arg.name, arg.vartype)
            self.current_fninfo = fninfo
            for stmt in fndef.body:
                stmt.accept(self)
        self.current_fninfo = None
        return VoidType

    def visit_forstmt(self, forstmt: ForStmt) -> VarType:
        rangeexpr = forstmt.range_expr
        start_type = rangeexpr.start.accept(self)
        if start_type != IntType:
            # TODO: add precise position information
            raise TypeCheckerError(
                f"ERROR: {forstmt.range_expr.start.span.start}: "
                f"for-loop start expression must be Int, but got `{start_type.name}`"
            )
        stop_type = rangeexpr.stop.accept(self)
        if stop_type != IntType:
            # TODO: add precise position information
            raise TypeCheckerError(
                f"ERROR: {forstmt.range_expr.stop.span.start}: "
                f"for-loop stop expression must be Int, but got `{stop_type.name}`"
            )

        with self.new_scope():
            # because start and end type are `Int`, loop_ident can also be defined
            # to be `Int`
            self.scope.define(forstmt.loop_ident.value, IntType)
            for stmt in forstmt.block:
                stmt.accept(self)

        return VoidType

    @contextmanager
    def new_scope(self) -> Generator[None, None, None]:
        try:
            self.scope = Scope(parent=self.scope)
            yield
        finally:
            old_scope = self.scope.parent
            assert old_scope is not None
            self.scope = old_scope

    def visit_doblock(self, doblock: DoBlock) -> VarType:
        with self.new_scope():
            for stmt in doblock.block:
                stmt.accept(self)
        return VoidType

    def visit_ifstmt(self, ifstmt: IfStmt) -> VarType:
        cond_type = ifstmt.condition.accept(self)
        if cond_type != BoolType:
            # TODO: add precise position information
            raise TypeCheckerError(
                f"if condition must be `Bool`, got `{cond_type.name}`"
            )

        with self.new_scope():
            for stmt in ifstmt.if_block:
                stmt.accept(self)

        for elif_ in ifstmt.elifs:
            elif_cond_type = elif_.condition.accept(self)
            if elif_cond_type != BoolType:
                raise TypeCheckerError(
                    f"elif condition must be `Bool`, got {elif_cond_type}"
                )
            with self.new_scope():
                for elifstmt in elif_.block:
                    elifstmt.accept(self)

        with self.new_scope():
            for elsestmt in ifstmt.else_block:
                elsestmt.accept(self)

        return VoidType

    def visit_returnstmt(self, returnstmt: ReturnStmt) -> VarType:
        assert self.current_fninfo is not None
        if returnstmt.expr is None:
            if self.current_fninfo.return_type != VoidType:
                raise TypeCheckerError(
                    f"ERROR at {returnstmt.ret_token.position}: return has type `{VoidType.name}`, but function `{self.current_fninfo.name}` is typed as `{self.current_fninfo.return_type.name}`"
                )
            return VoidType
        vartype = self.current_fninfo.return_type
        with self.expecting(vartype):
            ret_vartype = returnstmt.expr.accept(self)

        if self.current_fninfo.return_type != ret_vartype:
            raise TypeCheckerError(
                f"ERROR at {returnstmt.expr.span.start}: return has type `{ret_vartype.name}`, but function `{self.current_fninfo.name}` is typed as `{self.current_fninfo.return_type.name}`"
            )
        return ret_vartype

    def visit_exprstmt(self, exprstmt: ExprStmt) -> VarType:
        exprstmt.expr.accept(self)
        return VoidType

    def visit_array_assignment(self, array: ArrayAssign) -> VarType:
        name_vartype = self.scope.lookup(array.name.value)
        if name_vartype is None:
            raise TypeCheckerError(
                f"ERROR: {array.name.position}: `{array.name.value}` is not defined."
            )
        if not isinstance(name_vartype, ArrayType):
            raise TypeCheckerError(
                f"ERROR: {array.name.position}: Cannot index `{array.name.value}`: "
                f"expected an array, but found `{name_vartype.name}`."
            )
        index_vartype = array.index.accept(self)
        if index_vartype != IntType:
            raise TypeCheckerError(
                f"ERROR: {array.index.span.start}: Array index must be of type `Int`, but got `{index_vartype}`"
            )

        value_vartype = array.expr.accept(self)
        if name_vartype.vartype != value_vartype:
            raise TypeCheckerError(
                f"Expected type `{name_vartype.name}`, but got {value_vartype.name}"
            )
        return VoidType

    def visit_integerlit(self, intlit: IntegerLit) -> VarType:
        intlit.vartype = IntType
        return IntType

    def visit_stringlit(self, strlit: StringLit) -> VarType:
        strlit.vartype = StringType
        return StringType

    def visit_identifier(self, ident: Identifier) -> VarType:
        name = ident.token.value
        vartype = self.scope.lookup(name)
        if vartype is None:
            raise TypeCheckerError(
                f"ERROR: {ident.token.position}: `{name}` is not defined."
            )
        ident.vartype = vartype
        return vartype

    def visit_fncall(self, fncall: FnCall) -> VarType:
        # TODO: make it that I dont have to define the function before using it
        fnname = fncall.name.value
        fninfo = self.defined_fns.get(fnname)
        if fninfo is None:
            raise TypeCheckerError(
                f"ERROR: {fncall.name.position}: Undefined function `{fnname}`"
            )

        if len(fninfo.args) != len(fncall.args_list):
            raise TypeCheckerError(
                f"ERROR: {fncall.name.position}: "
                f"Function `{fnname}` expects {len(fninfo.args)} arguments, "
                f"but got {len(fncall.args_list)}"
            )

        for i, (fnarg, arg) in enumerate(zip(fninfo.args, fncall.args_list), start=1):
            expected = fnarg.vartype
            with self.expecting(expected):
                actual = arg.accept(self)
            param_name = "" if fnname in BUILTIN_FNS else f" `{fnarg.name}`"
            if expected != actual:
                raise TypeCheckerError(
                    f"ERROR: {fncall.name.position}: "
                    f"Type mismatch in call to `{fnname}`: "
                    f"expected `{expected.name}` for {i}. parameter{param_name}, "
                    f"but got `{actual.name}`"
                )

        fncall.vartype = fninfo.return_type
        return fninfo.return_type

    def visit_declaration(self, decl: Declaration) -> VarType:
        if decl.vartype == VoidType:
            raise TypeCheckerError(
                f"ERROR: {decl.name.position}: `Void` is not allowed as variable type"
            )
        if isinstance(decl.vartype, ArrayType) and decl.vartype.vartype == VoidType:
            raise TypeCheckerError(
                f"ERROR: {decl.name.position}: `Void` is not allowed as array type"
            )

        with self.expecting(decl.vartype):
            expr_vartype = decl.expr.accept(self)

        if decl.vartype != expr_vartype:
            raise TypeCheckerError(
                f"ERROR: {decl.expr.span.start}: "
                f"{decl.name.value} was typed as `{decl.vartype.name}`, but Expr evaluated to `{expr_vartype.name}`"
            )

        self.scope.define(decl.name.value, decl.vartype)
        return VoidType

    def visit_assignment(self, assign: Assignment) -> VarType:
        name = assign.name.value
        expected_type = self.scope.lookup(name)
        if expected_type is None:
            raise TypeCheckerError(
                f"ERROR at {assign.name.position}: "
                f"Cannot assign to `{name}` because it is not defined."
            )

        vartype = (
            expected_type.vartype
            if isinstance(expected_type, ArrayType)
            else expected_type
        )
        with self.expecting(vartype):
            actual_type = assign.expr.accept(self)

        if expected_type != actual_type:
            raise TypeCheckerError(
                f"ERROR at {assign.expr.span.start}: "
                f"Type mismatch in assignment to `{name}`. "
                f"Expected: `{expected_type.name}`, but got: `{actual_type.name}`"
            )
        return VoidType

    def visit_binary(self, binary: Binary) -> VarType:
        lhs_type = binary.lhs.accept(self)
        rhs_type = binary.rhs.accept(self)

        if lhs_type != rhs_type:
            raise TypeCheckerError(
                f"ERROR: {binary.operator.position}: "
                f"Type mismatch in binary expression: {lhs_type.name} {binary.operator.value} {rhs_type.name}"
            )

        if lhs_type == IntType and binary.operator.ttype in (
            TokenType.Plus,
            TokenType.Minus,
            TokenType.Star,
            TokenType.Slash,
            TokenType.Percent,
        ):
            binary.vartype = IntType
            return IntType

        binary.vartype = BoolType
        if lhs_type == IntType and binary.operator.ttype in (
            TokenType.Greater,
            TokenType.GreaterEqual,
            TokenType.Less,
            TokenType.LessEqual,
            TokenType.EqualEqual,
            TokenType.BangEqual,
        ):
            return BoolType

        if lhs_type == BoolType and binary.operator.ttype in (
            TokenType.Or,
            TokenType.And,
        ):
            return BoolType

        if lhs_type == StringType and binary.operator.ttype in (
            TokenType.EqualEqual,
            TokenType.BangEqual,
        ):
            return BoolType

        raise TypeCheckerError(
            f"ERROR: {binary.operator.position}: "
            f"Operator `{binary.operator.value}` is not supported between {lhs_type.name} and {rhs_type.name}"
        )

    def visit_unary(self, unary: Unary) -> VarType:
        expr_type = unary.expr.accept(self)
        if expr_type == IntType and unary.operator.ttype in (
            TokenType.Minus,
            TokenType.Plus,
        ):
            unary.vartype = IntType
            return IntType

        if expr_type == BoolType and unary.operator.ttype == TokenType.Not:
            unary.vartype = BoolType
            return BoolType

        raise TypeCheckerError(
            f"ERROR: {unary.expr.span.start}: "
            f"Unary operator `{unary.operator.value}` is not allowed on type `{expr_type.name}`. "
            f"Allowed types: "
            f"{'Int' if unary.operator.ttype in (TokenType.Plus, TokenType.Minus) else 'Bool'}"
        )

    def visit_grouping(self, grouping: Grouping) -> VarType:
        grouping.vartype = grouping.expr.accept(self)
        return grouping.vartype

    def visit_array_literal(self, array: ArrayLiteral) -> VarType:
        assert self.expected_vartype is not None

        if isinstance(self.expected_vartype, ArrayType):
            if len(array.items) == 0:
                raise TypeCheckerError(
                    f"ERROR: {array.span.start}: "
                    "Fixed-size arrays cannot have length 0."
                )
            if self.expected_vartype.length != len(array.items):
                raise TypeCheckerError(
                    f"ERROR: {array.span.start}: Fixed-size array length mismatch: "
                    f"Expected {self.expected_vartype.length}, got {len(array.items)}"
                )
        elif isinstance(self.expected_vartype, SliceType):
            pass
        else:
            assert False, f"unreachable: {self.expected_vartype.name}"

        exp_item_vt = self.expected_vartype.vartype
        for item in array.items:
            item_vt = item.accept(self)
            if exp_item_vt != item_vt:
                raise TypeCheckerError(
                    f"ERROR: {item.span.start}: Array element type mismatch: "
                    f"Expected `{exp_item_vt.name}`, got `{item_vt.name}`"
                )
        vartype = (
            ArrayType(exp_item_vt, len(array.items))
            if isinstance(self.expected_vartype, ArrayType)
            else SliceType(exp_item_vt)
        )
        array.vartype = vartype
        return vartype

    def visit_indexing(self, subscript: Subscript) -> VarType:
        name = subscript.name.value
        vartype = self.scope.lookup(name)
        if vartype is None:
            raise TypeCheckerError(
                f"ERROR: {subscript.name.position}: `{name}` is not defined."
            )

        index_vartype = subscript.index.accept(self)
        if index_vartype != IntType:
            raise TypeCheckerError(
                f"ERROR: {subscript.index.span.start}: Array Index must be an `Int`, but got `{index_vartype}`"
            )

        if isinstance(vartype, ArrayType) or isinstance(vartype, SliceType):
            subscript.vartype = vartype.vartype
            return vartype.vartype
        elif vartype == StringType:
            subscript.vartype = vartype
            return vartype
        else:
            raise TypeCheckerError(
                f"ERROR: {subscript.name.position}: Indexing `{name}` is not allowed. "
                f"`{name}` was defined as `{vartype.name}`. "
                "It is only allowed for type `Array` and `String`."
            )

    def visit_argv(self, argv: Argv) -> VarType:
        argv.expr.accept(self)
        argv.vartype = StringType
        return StringType

    def visit_booltrue(self, booltrue: BoolTrue) -> VarType:
        booltrue.vartype = BoolType
        return BoolType

    def visit_boolfalse(self, boolfalse: BoolFalse) -> VarType:
        boolfalse.vartype = BoolType
        return BoolType

    @contextmanager
    def expecting(self, vartype: VarType):
        old_expected = self.expected_vartype
        self.expected_vartype = vartype
        try:
            yield
        finally:
            self.expected_vartype = old_expected
