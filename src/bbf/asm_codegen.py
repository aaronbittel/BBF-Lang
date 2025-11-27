from __future__ import annotations

import math
from contextlib import contextmanager

import bbf.builtins as bbf_builtins
import bbf.nasm_macros as macros
from bbf.emitter import Emitter
from bbf.functions import FnInfo, FunctionTable
from bbf.lexer import TokenType
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
from bbf.nodes.program import Program, ProgTopLevelStmt
from bbf.nodes.stmt import (
    Assignment,
    Declaration,
    DoBlock,
    ExprStmt,
    ForStmt,
    IfStmt,
    IndexAssign,
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
    SymbolTable,
    VarType,
    VoidType,
)


class AsmCodeGen(Visitor):
    def __init__(self, emitter: Emitter, macros_emitter: Emitter) -> None:
        self.emitter = emitter
        self.macros_emitter = macros_emitter

        self.symbol_table = SymbolTable()
        self.function_table = FunctionTable()
        self.current_fn_returntype: VarType | None = None
        self.user_fndefs: list[FnDef] = []

        self.strings: list[str] = []
        self.arrays: list[tuple[str, list[str]]] = []

        self.is_slice = False

        self.if_label_count = 0
        self.elif_label_count = 0
        self.loop_count = 0
        self.or_true_count = 0
        self.or_end_count = 0
        self.and_false_count = 0
        self.and_end_count = 0

    def generate_prog(self, program: Program) -> None:
        self.nasm_macros()
        self.emitter.emit('%include "macros.asm"', indent=0)
        self.emitter.emit()
        self.program_prologue()
        self.emitter.emit("; program")
        program.accept(self)
        if self.symbol_table.reserved_space > 0:
            self.emitter.emit(f"FREE_SPACE {self.symbol_table.reserved_space} ")
        self.program_epilogue()
        if len(self.user_fndefs) > 0:
            self.user_defined_fns()
        self.builtins()
        self.static_section()
        self.bss_section()

    def visit_progtoplevelstmt(self, progtoplevelstmt: ProgTopLevelStmt) -> None:
        for stmt in progtoplevelstmt.stmts:
            stmt.accept(self)

    def visit_toplevelstmt(self, toplevelstmt: TopLevelStmt) -> None:
        toplevelstmt.stmt.accept(self)

    def visit_fndef(self, fndef: FnDef) -> None:
        self.function_table.define(FnInfo.from_node(fndef))
        self.user_fndefs.append(fndef)

    def visit_forstmt(self, stmt: ForStmt) -> None:
        loop_ident, range_expr, block = stmt.loop_ident, stmt.range_expr, stmt.block
        with self.new_scope():
            # NOTE: loop var is a new variable scoped to the loop scope
            loop_ident_offset = self.symbol_table.define(
                loop_ident.value, vartype=IntType
            )
            range_ident = self.symbol_table.lookup(loop_ident.value)
            assert range_ident is not None, f"{loop_ident.value} was just created"
            range_expr.start.accept(self)
            self.emitter.emit(f"STORE_VAR {loop_ident_offset:+d} ; range_start[Int]")
            self.emitter.emit(f"RESERVE_SPACE {IntType.stack_size} ; loop var")
            # TODO: move creating lables into function
            self.emitter.emit(f".loop_{self.loop_count}_start:", indent=0)
            range_expr.stop.accept(self)
            self.emitter.emit("pop rax ; range end")
            self.emitter.emit(
                f"cmp qword [rbp{range_ident.offset:+d}], rax ; check if condition"
            )
            if range_expr.inclusive:
                self.emitter.emit(f"jg .loop_{self.loop_count}_end")
            else:
                self.emitter.emit(f"jge .loop_{self.loop_count}_end")

            for s in block.stmts:
                s.accept(self)
            self.emitter.emit(
                f"inc qword [rbp{range_ident.offset:+d}] ; increment loop variable"
            )
            self.emitter.emit(f"jmp .loop_{self.loop_count}_start")
            self.emitter.emit(f".loop_{self.loop_count}_end:", indent=0)
        self.loop_count += 1

    def visit_doblock(self, doblock: DoBlock) -> None:
        with self.new_scope():
            for stmt in doblock.block:
                stmt.accept(self)

    def visit_ifstmt(self, ifstmt: IfStmt) -> None:
        label_id = self.if_label_count
        self.if_label_count += 1

        end_label = f".end_if_{label_id}_label"
        else_label = f".else_{label_id}_label"

        # --- IF condition ---
        ifstmt.condition.accept(self)
        self.emitter.emit("pop rax")
        self.emitter.emit("cmp rax, FALSE")
        next_label = end_label
        if len(ifstmt.elifs) > 0:
            next_label = f".elif_{label_id}_0_label"
        elif ifstmt.else_block is not None:
            next_label = else_label
        self.emitter.emit(f"je {next_label}")

        # --- IF block ---
        with self.new_scope():
            for s in ifstmt.if_block:
                s.accept(self)
        self.emitter.emit(f"jmp {end_label}")

        # --- ELIF chain ---
        if len(ifstmt.elifs) > 0:
            for i, elif_block in enumerate(ifstmt.elifs):
                this_label = f".elif_{label_id}_{i}_label: ; THIS LABEL"
                next_label = end_label
                if i + 1 < len(ifstmt.elifs):  # there is a next elif block
                    next_label = f".elif_{label_id}_{i + 1}_label ; NEXT LABEL"
                elif ifstmt.else_block is not None:  # there is a else block
                    next_label = else_label
                self.emitter.emit(this_label, indent=0)
                elif_block.condition.accept(self)
                self.emitter.emit("pop rax")
                self.emitter.emit("cmp rax, FALSE")
                self.emitter.emit(f"je {next_label}")
                with self.new_scope():
                    for s in elif_block.block:
                        s.accept(self)
                self.emitter.emit(f"jmp {end_label}")

        # --- ELSE block ---
        self.emitter.emit(f"{else_label}:", indent=0)
        if ifstmt.else_block:
            with self.new_scope():
                for s in ifstmt.else_block:
                    s.accept(self)

        # --- END ---
        self.emitter.emit(f"{end_label}:", indent=0)

    def visit_returnstmt(self, returnstmt: ReturnStmt) -> None:
        if returnstmt.expr is not None:
            returnstmt.expr.accept(self)
            assert self.current_fn_returntype is not None, "unreachable"
            if not self.current_fn_returntype.is_slice:
                self.emitter.emit("pop rax")
            else:
                self.emitter.emit("pop rdi")
                self.emitter.emit("pop rax")
        self.emitter.emit("jmp .epilogue")

    def visit_exprstmt(self, expr_stmt: ExprStmt) -> None:
        expr_stmt.expr.accept(self)

    def visit_index_assign(self, index_assign: IndexAssign) -> None:
        varinfo = self.symbol_table.lookup(index_assign.target.value)
        assert varinfo is not None, "TypeChecker: Bug"
        assert isinstance(varinfo.vartype, ArrayType), (
            "TypeChecker should have checked this"
        )
        assert varinfo.vartype.vartype in (IntType, BoolType, StringType), (
            "TypeChecker: Bug"
        )

        index_assign.index.accept(self)
        self.emitter.emit("pop rcx ; index")
        index_assign.value.accept(self)
        self.emitter.emit("pop r9 ; new value")
        self.emitter.emit(f"mov rax, [rbp{varinfo.offset}]")
        self.emitter.emit("imul rcx, 8")
        self.emitter.emit("add rax, rcx")
        self.emitter.emit("mov qword [rax], r9")

    def visit_integerlit(self, intlit: IntegerLit) -> None:
        self.emitter.emit(f"PUSH_INT {intlit.token.value}")

    def visit_stringlit(self, strlit: StringLit) -> None:
        for i, s in enumerate(self.strings):
            if s == strlit.token.value:
                str_label = make_string_label(i)
                len_label = f"{str_label}_len"
                break
        else:
            str_label, len_label = self.add_string(strlit.token.value)

        self.emitter.emit(f"PUSH_SLICE {str_label}, {len_label}")

    def visit_identifier(self, ident: Identifier) -> None:
        # FIX: hack: Improve when implementing globals?
        if ident.token.value == "argc":
            self.emitter.emit("PUSH_ARGC")
            return
        varinfo = self.symbol_table.lookup(ident.token.value)
        assert varinfo is not None, "TypeChecker: Bug"
        if not varinfo.vartype.is_slice:
            self.emitter.emit(
                f"PUSH_VAR {varinfo.offset:+d} ; var: {ident.token.value}"
            )
        else:
            self.emitter.emit(
                f"PUSH_VAR {varinfo.offset:+d} ; str_ptr: {ident.token.value}"
            )
            self.emitter.emit(
                f"PUSH_VAR {varinfo.offset - 8:+d} ; str_len: {ident.token.value}"
            )

    def visit_fncall(self, fncall: FnCall) -> None:
        # NOTE: Functions will push their result into rax. Calling code needs to
        # handle this.
        fninfo = self.function_table.lookup(fncall.name.value)
        assert fninfo is not None, "TypeChecker: Bug"

        regs_order = ["rdi", "rsi", "rdx", "rcx", "r8", "r9"]
        reg_i = 0

        if isinstance(fninfo.return_type, ArrayType):
            self.emitter.emit(f"RESERVE_SPACE {fninfo.return_type.total_size}")
            self.emitter.emit("lea rdi, [rsp]")
            reg_i += 1
            self.symbol_table.reserve(fninfo.return_type.total_size)

        self.emitter.emit(f"; {fninfo.name} function args")
        for fn_arg, expr_arg in zip(fninfo.args, fncall.args_list):
            expr_arg.accept(self)
            if not fn_arg.vartype.is_slice:
                assert reg_i < len(regs_order), (
                    "Currently can't handle more physcial args than 6"
                )
                self.emitter.emit(f"pop {regs_order[reg_i]}")
                reg_i += 1
            else:
                assert reg_i + 1 < len(regs_order), (
                    "Currently can't handle more physcial args than 6"
                )
                self.emitter.emit(f"pop {regs_order[reg_i + 1]} ; str_len")
                self.emitter.emit(f"pop {regs_order[reg_i]} ; str_ptr")
                reg_i += 2

        self.emitter.emit(
            f"call {fninfo.callname} ; return_type: {fninfo.return_type.name}"
        )
        if fninfo.return_type == VoidType:
            return
        if not fninfo.return_type.is_slice:
            self.emitter.emit("push rax ; return value from fn call")
        else:
            self.emitter.emit("push rax ; return ptr from fn call")
            self.emitter.emit("push rdi ; return len from fn call")

    def visit_declaration(self, decl: Declaration) -> None:
        name, expr = decl.name, decl.expr

        offset = self.symbol_table.define(name.value, decl.vartype)
        self.emitter.emit(f"RESERVE_SPACE {decl.vartype.stack_size}")

        if isinstance(decl.vartype, SliceType):
            self.is_slice = True
        expr.accept(self)

        if self.is_slice:  # SliceType
            self.emitter.emit(f"STORE_VAR {offset - 16:+d} ; cap[Int]: {name.value}")
            self.emitter.emit(f"STORE_VAR {offset - 8:+d} ; len[Int]: {name.value}")
            self.emitter.emit(f"STORE_VAR {offset:+d} ; ptr[Int]: {name.value}")
        elif not decl.vartype.is_slice:
            self.emitter.emit(f"STORE_VAR {offset:+d} ; var[Int]: {name.value}")
        else:
            self.emitter.emit(f"STORE_VAR {offset - 8:+d} ; len[String]: {name.value}")
            self.emitter.emit(f"STORE_VAR {offset:+d} ; ptr[String]: {name.value}")
        self.is_slice = False

    def visit_assignment(self, assign: Assignment) -> None:
        name, expr = assign.name, assign.expr
        expr.accept(self)

        varinfo = self.symbol_table.lookup(name.value)
        assert varinfo is not None, "TypeChecker: Bug"
        if not varinfo.vartype.is_slice:
            self.emitter.emit(
                f"STORE_VAR {varinfo.offset:+d} ; var[{varinfo.vartype.name}]: {name.value}"
            )
        else:
            # TODO: Should array full assignments be handled here?
            assert not isinstance(varinfo.vartype, ArrayType)
            self.emitter.emit(
                f"STORE_VAR {varinfo.offset - 8:+d} ; len[String]: {name.value}"
            )
            self.emitter.emit(
                f"STORE_VAR {varinfo.offset:+d} ; ptr[String]: {name.value}"
            )

    def visit_binary(self, binary: Binary) -> None:
        assert binary.lhs.vartype == binary.rhs.vartype, "TypeChecker: Bug"
        if binary.lhs.vartype == StringType:
            binary.lhs.accept(self)
            binary.rhs.accept(self)
            self.emitter.emit("pop rcx ; len rhs")
            self.emitter.emit("pop rdx ; ptr rhs")
            self.emitter.emit("pop rsi ; len lhs")
            self.emitter.emit("pop rdi ; ptr lhs")
            self.emitter.emit("call __builtin_strcmp")
            if binary.operator.ttype == TokenType.EqualEqual:
                pass
            elif binary.operator.ttype == TokenType.BangEqual:
                self.emitter.emit("xor rax, 1")
            else:
                assert False, "TypeChecker: Bug"
            self.emitter.emit("push rax")
        elif binary.lhs.vartype == IntType:
            binary.lhs.accept(self)
            binary.rhs.accept(self)
            if binary.operator.ttype == TokenType.Plus:
                self.emitter.emit("PUSH_BINARY_ADD")
            elif binary.operator.ttype == TokenType.Minus:
                self.emitter.emit("PUSH_BINARY_SUB")
            elif binary.operator.ttype == TokenType.Star:
                self.emitter.emit("PUSH_BINARY_MUL")
            elif binary.operator.ttype == TokenType.Slash:
                self.emitter.emit("PUSH_BINARY_DIV")
            elif binary.operator.ttype == TokenType.Percent:
                self.emitter.emit("PUSH_BINARY_MOD")
            elif binary.operator.ttype in COMPARISON_SETCC:
                mnemonic = COMPARISON_SETCC[binary.operator.ttype]
                self.emitter.emit(f"PUSH_INT_COMPARE {mnemonic}")
            else:
                assert False, f"unreachable binary operator: {binary.operator.ttype}"
        elif binary.lhs.vartype == BoolType:
            if binary.operator.ttype == TokenType.Or:
                or_true_label = self.or_true_label()
                or_end_label = self.or_end_label()

                binary.lhs.accept(self)
                self.emitter.emit(f"CHECK_BOOL_JUMP {or_true_label}, TRUE")

                binary.rhs.accept(self)
                self.emitter.emit(f"CHECK_BOOL_JUMP {or_true_label}, TRUE")

                self.emitter.emit("; or evaluated to false")
                self.emitter.emit("push FALSE")
                self.emitter.emit(f"jmp {or_end_label}")

                self.emitter.emit(f"{or_true_label}:", indent=0)
                self.emitter.emit("push TRUE")
                self.emitter.emit(f"{or_end_label}:", indent=0)
            elif binary.operator.ttype == TokenType.And:
                and_false_label = self.and_false_label()
                and_end_label = self.and_end_label()

                binary.lhs.accept(self)
                self.emitter.emit(f"CHECK_BOOL_JUMP {and_false_label}, FALSE")

                binary.rhs.accept(self)
                self.emitter.emit(f"CHECK_BOOL_JUMP {and_false_label}, FALSE")

                self.emitter.emit("; and evaluated to true")
                self.emitter.emit("push TRUE")
                self.emitter.emit(f"jmp {and_end_label}")

                self.emitter.emit(f"{and_false_label}:", indent=0)
                self.emitter.emit("push FALSE")
                self.emitter.emit(f"{and_end_label}:", indent=0)
            else:
                assert False, f"unreachable binary operator: {binary.operator.ttype}"
        else:
            assert False, "unreachable"

    def visit_unary(self, unary: Unary) -> None:
        unary.expr.accept(self)
        if unary.operator.ttype == TokenType.Minus:
            self.emitter.emit("PUSH_NEGATE")
        elif unary.operator.ttype == TokenType.Not:
            self.emitter.emit("PUSH_INT 0")
            self.emitter.emit("PUSH_INT_COMPARE setle")
        elif unary.operator.ttype == TokenType.Plus:
            pass  # Ignore "+"
        else:
            assert False, "TypeChecker: Bug"

    def visit_grouping(self, grouping: Grouping) -> None:
        grouping.expr.accept(self)

    def visit_argv(self, argv: Argv) -> None:
        argv.expr.accept(self)
        self.emitter.emit("PUSH_ARGV_STRING")

    def visit_array_literal(self, array: ArrayLiteral) -> None:
        # array declaration outside of a function -> .data static memory
        if self.current_fn_returntype is None:
            if self.is_slice:
                assert (
                    isinstance(array.vartype, SliceType)
                    and array.vartype.vartype == IntType
                )
                self.emitter.emit("PUSH_MEM_PTR")
                self.emitter.emit("pop r10")
                for i, item in enumerate(array.items):
                    item.accept(self)
                    self.emitter.emit("pop rax")
                    self.emitter.emit(f"mov [r10 + {i} * 8], rax")

                cap = calculate_slice_capacity(len(array.items))
                self.emitter.emit(f"ADD_MEM_PTR {cap}, 8")

                self.emitter.emit("push r10")
                self.emitter.emit(f"push {len(array.items)}")
                self.emitter.emit(f"push {cap}")
                return
            else:
                if isinstance(array.items[0], StringLit):
                    str_literals = extract_literals(array)
                    arr: list[str] = []
                    for s in str_literals:
                        str_label, len_label = self.add_string(s)
                        arr.append(str_label)
                        arr.append(len_label)
                    self.arrays.append(("slice", arr))
                else:
                    self.arrays.append(("primitive", extract_literals(array)))
                array_label = make_array_label(len(self.arrays) - 1)
                len_label = f"{array_label}_len"
                self.emitter.emit(f"PUSH_SLICE {array_label}, {len_label}")
                return
        # array declaration inside a function -> ptr to space in rdi
        for i, item in enumerate(array.items):
            item.accept(self)
            self.emitter.emit("pop rax")
            self.emitter.emit(f"mov [rdi + {i * 8}], rax")

        self.emitter.emit("push rdi")
        assert isinstance(self.current_fn_returntype, ArrayType)
        self.emitter.emit(f"PUSH_INT {self.current_fn_returntype.length}")

    def visit_indexing(self, subscript: Indexing) -> None:
        varinfo = self.symbol_table.lookup(subscript.name.value)
        assert varinfo is not None, "TypeChecker: Bug"

        if isinstance(varinfo.vartype, ArrayType):
            assert varinfo.vartype.vartype in (IntType, BoolType, StringType), (
                "TypeChecker: Bug"
            )

            if not varinfo.vartype.vartype.is_slice:
                subscript.index.accept(self)
                self.emitter.emit(f"PUSH_INDEXED_SCALAR {varinfo.offset:+d}")
            else:
                assert not isinstance(varinfo.vartype.vartype, ArrayType), (
                    "Nested arrays are currently not supported"
                )
                subscript.index.accept(self)
                self.emitter.emit(f"PUSH_INDEXED_SLICE {varinfo.offset:+d}")
        elif isinstance(varinfo.vartype, SliceType):
            subscript.index.accept(self)
            self.emitter.emit(f"PUSH_INDEXED_SCALAR {varinfo.offset:+d}")
        elif varinfo.vartype == StringType:
            subscript.index.accept(self)
            self.emitter.emit(f"PUSH_STRING_ELEM {varinfo.offset:+d}")
        else:
            assert False, "TypeChecker: Bug"

    def visit_booltrue(self, booltrue: BoolTrue) -> None:
        self.emitter.emit("PUSH_BOOL TRUE")

    def visit_boolfalse(self, boolfalse: BoolFalse) -> None:
        self.emitter.emit("PUSH_BOOL FALSE")

    @contextmanager
    def new_scope(self, is_function: bool = False):
        try:
            starting_offset = -8 if is_function else self.symbol_table.next_offset
            self.symbol_table = SymbolTable(
                parent=self.symbol_table, next_offset=starting_offset
            )
            yield
        finally:
            self.emitter.emit(f"FREE_SPACE {self.symbol_table.reserved_space} ; scope")
            old_table = self.symbol_table.parent
            assert old_table is not None
            self.symbol_table = old_table

    def nasm_macros(self) -> None:
        self.macros_emitter.emit("%define TRUE 1", indent=0)
        self.macros_emitter.emit("%define FALSE 0", indent=0)
        for name, code in vars(macros).items():
            if name.startswith("_macro_"):
                self.macros_emitter.multi(code)

    def program_prologue(self) -> None:
        self.emitter.emit("global __sys_mmap", indent=0)
        self.emitter.emit("global _start", indent=0)
        self.emitter.emit("", indent=0)
        self.emitter.emit("_start:", indent=0)
        self.emitter.emit("PROGRAM_PROLOGUE")

    def program_epilogue(self):
        self.emitter.emit()
        self.emitter.emit("; default exit 0")
        self.emitter.emit("mov rdi, 0")
        self.emitter.emit("call __sys_exit")

    def user_defined_fns(self):
        self.emitter.emit()
        self.emitter.emit("; USER FUNCTIONS", indent=0)
        self.emitter.emit()
        for fndef in self.user_fndefs:
            self.current_fn_returntype = fndef.ret_vartype
            assert len(fndef.params) <= 6, (
                "Functions with more than 6 params (next param on the stack) are currently not supported"
            )

            self.emitter.emit("; arg0 | arg1 | arg2 | arg3 | arg4 | arg5", indent=0)
            self.emitter.emit("; rdi  | rsi  | rdx  | rcx  |  r8  |  r9", indent=0)
            self.emitter.emit(f"{fndef.name.value}:", indent=0)

            self.emitter.emit("FN_PROLOGUE")
            self.emitter.emit()

            reg_order = ["rdi", "rsi", "rdx", "rcx", "r8", "r9"]
            reg_i = 0

            with self.new_scope(is_function=True):
                if isinstance(fndef.ret_vartype, ArrayType):
                    self.emitter.emit("RESERVE_SPACE 8 ; internal array ptr")
                    self.symbol_table.reserve(8)
                    reg_i += 1

                for param in fndef.params:
                    vartype = param.vartype
                    self.emitter.emit(
                        f"RESERVE_SPACE {vartype.stack_size} ; param {param.name.value}"
                    )
                    offset = self.symbol_table.define(param.name.value, vartype)

                    if not vartype.is_slice:
                        assert reg_i <= 5, (
                            "More than 6 registers used (strings take up 2)"
                        )
                        self.emitter.emit(f"mov [rbp{offset:+d}], {reg_order[reg_i]}")
                        reg_i += 1
                    else:
                        assert reg_i + 1 <= 5, (
                            "More than 6 registers used (strings take up 2)"
                        )
                        self.emitter.emit(
                            f"mov [rbp{offset:+d}], {reg_order[reg_i]} ; store str_ptr"
                        )
                        self.emitter.emit(
                            f"mov [rbp{offset - 8:+d}], {reg_order[reg_i + 1]} ; store str_len"
                        )
                        reg_i += 2

                self.emitter.emit("; fn body")
                for stmt in fndef.body:
                    stmt.accept(self)

            self.emitter.emit()
            self.emitter.emit(".epilogue:", indent=0)
            self.emitter.emit("FN_EPILOGUE")
            self.current_fn_returntype = None

    def builtins(self) -> None:
        self.emitter.emit("")
        self.emitter.emit("; BUILTIN FUNCTIONS", indent=0)

        for name, code in vars(bbf_builtins).items():
            if name.startswith("_builtin_"):
                self.emitter.multi(code)

    def static_section(self) -> None:
        self.emitter.emit("")
        self.emitter.emit("; STATIC SECTION", indent=0)
        self.emitter.emit("section .data", indent=0)
        self.emitter.emit('__true: db "true"')
        self.emitter.emit("__true_len: equ $ - __true")
        self.emitter.emit('__false: db "false"')
        self.emitter.emit("__false_len: equ $ - __false")
        for i, raw_s in enumerate(self.strings):
            label = make_string_label(i)
            nasm_str = encode_nasm_string(raw_s)
            output = f"{nasm_str}, 0" if nasm_str != "" else "0"
            self.emitter.emit(f"{label}: db {output}")
            self.emitter.emit(f"{label}_len: equ $ - {label} - 1")
        for i, (arr_type, array) in enumerate(self.arrays):
            if arr_type == "primitive":
                label = make_array_label(i)
                self.emitter.emit(f"{label}: dq {', '.join(n for n in array)}")
                self.emitter.emit(f"{label}_len: equ ($ - {label}) / 8")
            elif arr_type == "slice":
                label = make_array_label(i)
                self.emitter.emit(f"{label}:")
                for arr in array:
                    self.emitter.emit(f"dq {arr}", indent=8)
                self.emitter.emit(f"{label}_len: equ ($ - {label}) / 8")
            else:
                assert False, "unreachable"

    def bss_section(self) -> None:
        self.emitter.emit("")
        self.emitter.emit("section .bss", indent=0)
        self.emitter.emit("__mem_ptr: resq 1")
        self.emitter.emit("__argc: resq 1")
        self.emitter.emit("__argv: resq 1")
        self.emitter.emit("__itoa_buf: resb 32")

    def add_string(self, s: str) -> tuple[str, str]:
        self.strings.append(s)
        str_label = make_string_label(len(self.strings) - 1)
        len_label = f"{str_label}_len"
        return str_label, len_label

    def or_true_label(self) -> str:
        lbl = f".or_true_{self.or_true_count}"
        self.or_true_count += 1
        return lbl

    def or_end_label(self) -> str:
        lbl = f".or_end_{self.or_end_count}"
        self.or_end_count += 1
        return lbl

    def and_false_label(self) -> str:
        lbl = f".and_false_{self.and_false_count}"
        self.and_false_count += 1
        return lbl

    def and_end_label(self) -> str:
        lbl = f".and_end_{self.and_end_count}"
        self.and_end_count += 1
        return lbl


def extract_literals(array: ArrayLiteral) -> list[str]:
    # NOTE: typechecker assures that all values are of the same type
    def _encode_ints(ints: list[Expr]) -> list[str]:
        out: list[str] = []
        for i in ints:
            assert isinstance(i, IntegerLit)
            out.append(i.token.value)
        return out

    def _encode_bools(bools: list[Expr]) -> list[str]:
        out: list[str] = []
        for b in bools:
            if isinstance(b, BoolTrue):
                v = "TRUE"
            elif isinstance(b, BoolFalse):
                v = "FALSE"
            else:
                assert False, "unreachable"
            out.append(v)
        return out

    def _encode_strings(strings: list[Expr]) -> list[str]:
        out: list[str] = []
        for s in strings:
            assert isinstance(s, StringLit)
            out.append(s.token.value)
        return out

    if isinstance(array.items[0], IntegerLit):
        return _encode_ints(array.items)
    if isinstance(array.items[0], BoolTrue) or isinstance(array.items[0], BoolFalse):
        return _encode_bools(array.items)
    if isinstance(array.items[0], StringLit):
        return _encode_strings(array.items)
    raise ValueError(f"Unknown type for array literal: `{type(array.items[0])}`")


def encode_nasm_string(string: str) -> str:
    def _insert_escaped_code(i: int, code: int) -> str:
        if i == 0:  # <newline> as first character
            return f"{code}" if len(string) == 1 else f'{code}, "'
        if len(string) - 1 == i:  # <newline> as last character
            return f'", {code}'
        # inbetween words
        return f'", {code}, "'

    output = ""
    for i, ch in enumerate(string):
        if ch == "\n":
            output += _insert_escaped_code(i=i, code=10)
        elif ch == "\t":
            output += _insert_escaped_code(i=i, code=9)
        elif ch == '"':
            output += _insert_escaped_code(i=i, code=34)
        elif ch == "'":
            output += _insert_escaped_code(i=i, code=39)
        else:
            if output == "":
                output = '"'
            output += ch
            if i == len(string) - 1:
                output += '"'
    return output


def make_array_label(i: int) -> str:
    return f"arr_{i:02}"


def make_string_label(i: int) -> str:
    return f"s_lit_{i:02}"


class CodeGenError(Exception):
    pass


COMPARISON_SETCC = {
    TokenType.Less: "setl",  # <
    TokenType.LessEqual: "setle",  # <=
    TokenType.Greater: "setg",  # >
    TokenType.GreaterEqual: "setge",  # >=
    TokenType.EqualEqual: "sete",  # ==
    TokenType.BangEqual: "setne",  # !=
}

MIN_SLICE_CAPACITY = 8


def calculate_slice_capacity(length: int) -> int:
    # This ensures that capacity > length. Because currently no freeing of allocatated
    # memory is implemented.
    if length == 0:
        return MIN_SLICE_CAPACITY
    return int(max(MIN_SLICE_CAPACITY, 2 ** (1 + math.ceil(math.log2(length)))))
