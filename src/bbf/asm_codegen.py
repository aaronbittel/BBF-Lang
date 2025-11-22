from __future__ import annotations

from contextlib import contextmanager

import bbf.builtins as bbf_builtins
from bbf.emitter import Emitter
from bbf.functions import FnInfo, FunctionTable
from bbf.lexer import TokenType
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
from bbf.nodes.program import Program, ProgTopLevelStmt
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
from bbf.varinfo import SymbolTable, VarType


class AsmCodeGen(Visitor):
    def __init__(self, emitter: Emitter) -> None:
        self.emitter = emitter

        self.symbol_table = SymbolTable()
        self.function_table = FunctionTable()
        self.strings: list[str] = []
        self.if_label_count = 0
        self.elif_label_count = 0
        self.loop_count = 0
        self.comparison_count = 0
        self.user_fndefs: list[FnDef] = []
        self.or_true_count = 0
        self.or_end_count = 0
        self.and_false_count = 0
        self.and_end_count = 0

    def generate_prog(self, program: Program) -> None:
        self.program_prologue()
        self.emitter.emit("; program")
        program.accept(self)
        if self.symbol_table.reserved_space > 0:
            self.emitter.emit(
                f"add rsp, {self.symbol_table.reserved_space} ; free reserved space"
            )
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
                loop_ident.value, vartype=VarType.Int
            )
            range_expr.start.accept(self)
            self.emitter.emit("pop rax ; loop var")
            self.emitter.emit(
                f"sub rsp, {VarType.Int.size} ; reserve space for loop var"
            )
            range_ident = self.symbol_table.lookup(loop_ident.value)
            assert range_ident is not None, f"{loop_ident.value} was just created"
            self.emitter.emit(f"mov [rbp{loop_ident_offset:+d}], rax")
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
        self.emitter.emit("cmp rax, 0")
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
                self.emitter.emit("cmp rax, 0")
                self.emitter.emit(f"je {next_label}")
                with self.new_scope():
                    for s in elif_block.block:
                        s.accept(self)
                self.emitter.emit(f"jmp {end_label}")
                # self.emitter.emit(f"{next_label}:", indent=0)

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
            self.emitter.emit("pop rax")
        self.emitter.emit("jmp .epilogue")

    def visit_exprstmt(self, expr_stmt: ExprStmt) -> None:
        expr_stmt.expr.accept(self)

    def visit_integerlit(self, intlit: IntegerLit) -> None:
        self.emitter.emit(f"mov rax, {intlit.token.value}")
        self.emitter.emit("push rax")

    def visit_stringlit(self, strlit: StringLit) -> None:
        self.strings.append(strlit.token.value)
        label = make_string_label(len(self.strings) - 1)
        len_label = f"{label}_len"
        self.emitter.emit("; load string literal")
        self.emitter.emit("; push string addr")
        self.emitter.emit(f"lea rax, [{label}]")
        self.emitter.emit("push rax")
        self.emitter.emit("; push string length")
        self.emitter.emit(f"push qword [{len_label}]")

    def visit_identifier(self, ident: Identifier) -> None:
        # FIX: hack: Improve when implementing globals?
        if ident.token.value == "argc":
            self.emitter.emit("push qword [__argc]")
            return
        varinfo = self.symbol_table.lookup(ident.token.value)
        if varinfo is None:
            is_numeric_with_underscores = lambda value: all(
                ch.isdigit() or ch == "_" for ch in value
            )
            extra = (
                " Did you mean to write a number?"
                if is_numeric_with_underscores(ident.token.value)
                else ""
            )
            raise CodeGenError(
                f"ERROR: {ident.token.position}: identifier `{ident.token.value}` was not defined.{extra}"
            )
        if varinfo.vartype in (VarType.Int, VarType.Bool):
            self.emitter.emit(
                f"push qword [rbp{varinfo.offset:+d}] ; push value from variable {ident.token.value}"
            )
        elif varinfo.vartype == VarType.String:
            self.emitter.emit(
                f"push qword [rbp{varinfo.offset:+d}] ; str_ptr form variable {ident.token.value}"
            )
            self.emitter.emit(
                f"push qword [rbp{varinfo.offset - 8:+d}] ; str_len form variable {ident.token.value}"
            )
        else:
            assert False, f"unreachable: unknown VarType: {varinfo.vartype}"

    def visit_fncall(self, stmt: FnCall) -> None:
        # NOTE: Functions will push their result into rax. Calling code needs to
        # handle this.
        fninfo = self.function_table.lookup(stmt.name.value)
        if fninfo is None:
            raise CodeGenError(
                f"ERROR: {stmt.name.position}: No function with name `{stmt.name.value}` is defined."
            )
        fn_name = stmt.name.value

        regs_order = ["rdi", "rsi", "rdx", "rcx", "r8", "r9"]
        reg_i = 0

        self.emitter.emit(f"; {fn_name} function args")
        for fn_arg, expr_arg in zip(fninfo.args, stmt.args_list):
            expr_arg.accept(self)
            if fn_arg.vartype in (VarType.Int, VarType.Bool):
                assert reg_i < len(regs_order), (
                    "Currently can't handle more physcial args than 6"
                )
                self.emitter.emit(f"pop {regs_order[reg_i]}")
                reg_i += 1
            elif fn_arg.vartype == VarType.String:
                assert reg_i + 1 < len(regs_order), (
                    "Currently can't handle more physcial args than 6"
                )
                self.emitter.emit(f"pop {regs_order[reg_i + 1]} ; str_len")
                self.emitter.emit(f"pop {regs_order[reg_i]} ; str_ptr")
                reg_i += 2
            else:
                raise CodeGenError(
                    f"ERROR: Unexpected vartype `{fn_arg.vartype}` for `{fn_arg.name}` in `{fn_name}`"
                )

        self.emitter.emit(f"call {fn_name} ; return_type: {fninfo.return_type.name}")
        if fninfo.return_type in (VarType.Int, VarType.Bool):
            self.emitter.emit("push rax ; return value from fn call")
        elif fninfo.return_type == VarType.Void:
            pass
        elif fninfo.return_type == VarType.String:
            self.emitter.emit("push rax ; return str_ptr from fn call")
            self.emitter.emit("push rdi ; return str_len from fn call")
        else:
            raise CodeGenError(
                f"ERROR: {stmt.name.position}: return type {fninfo.return_type} is currently not supported."
            )

    def visit_declaration(self, decl: Declaration) -> None:
        name, expr = decl.name, decl.expr

        self.emitter.emit(f"sub rsp, {decl.vartype.size} ; reserve space for decl")
        expr.accept(self)
        offset = self.symbol_table.define(name.value, decl.vartype)

        if decl.vartype in (VarType.Int, VarType.Bool):
            self.emitter.emit("pop rax")
            self.emitter.emit(f"mov [rbp{offset:+d}], rax")
        elif decl.vartype == VarType.String:
            self.emitter.emit("pop rdx ; str_len")
            self.emitter.emit("pop rax ; str_ptr")
            self.emitter.emit(f"mov [rbp{offset:+d}], rax ; store str_ptr")
            self.emitter.emit(f"mov [rbp{offset - 8:+d}], rdx ; store str_len")
        else:
            raise CodeGenError(
                f"ERROR: {name.position}: Unsupported VarType `{decl.vartype}`"
            )

    def visit_assignment(self, assign: Assignment) -> None:
        name, expr = assign.name, assign.expr
        expr.accept(self)

        varinfo = self.symbol_table.lookup(name.value)
        if varinfo is None:
            raise CodeGenError(
                f"ERROR: {name.position}: undeclared variable `{name.value}`. Did you forget to assign a type?"
            )
        self.emitter.emit("pop rax")
        self.emitter.emit(f"mov [rbp{varinfo.offset:+d}], rax")

    def visit_binary(self, binary: Binary) -> None:
        if binary.operator.ttype not in (TokenType.Or, TokenType.And):
            binary.lhs.accept(self)
            binary.rhs.accept(self)

            self.emitter.emit("pop rbx; pop rhs")
            self.emitter.emit("pop rax; pop lhs")
            if binary.operator.ttype == TokenType.Plus:
                self.emitter.emit("; addition")
                self.emitter.emit("add rax, rbx")
                self.emitter.emit("push rax")
            elif binary.operator.ttype == TokenType.Minus:
                self.emitter.emit("; subtraction")
                self.emitter.emit("sub rax, rbx")
                self.emitter.emit("push rax")
            elif binary.operator.ttype == TokenType.Star:
                self.emitter.emit("; multiplication")
                self.emitter.emit("cqo ; fill rdx to fit negative or positive number")
                self.emitter.emit("imul rbx")
                self.emitter.emit("push rax")
            elif binary.operator.ttype == TokenType.Slash:
                self.emitter.emit("; division")
                self.emitter.emit("cqo ; fill rdx to fit negative or positive number")
                self.emitter.emit("idiv rbx")
                self.emitter.emit("push rax")
            elif binary.operator.ttype == TokenType.Percent:
                self.emitter.emit("; modulo")
                self.emitter.emit("cqo ; fill rdx to fit negative or positive number")
                self.emitter.emit("idiv rbx")
                self.emitter.emit("push rdx ; (remainder always in rdx)")
            elif binary.operator.ttype in COMPARISON_SETCC:
                setcc_mnemonic = COMPARISON_SETCC[binary.operator.ttype]
                self.emitter.emit("cmp rax, rbx")
                self.emitter.emit(f"{setcc_mnemonic} al ; set AL = 1 if condition")
                self.emitter.emit("movzx rax, al ; zero-extend AL to RAX")
                self.emitter.emit("push rax")
                self.comparison_count += 1
            else:
                assert False, f"unreachable binary operator: {binary.operator.ttype}"
        else:
            if binary.operator.ttype == TokenType.Or:
                or_true_label = self.or_true_label()
                or_end_label = self.or_end_label()

                binary.lhs.accept(self)
                self.emitter.emit("; or lhs")
                self.emitter.emit("pop rax")
                self.emitter.emit("cmp rax, 1 ; test true")
                self.emitter.emit(f"je {or_true_label}")

                binary.rhs.accept(self)
                self.emitter.emit("; or rhs")
                self.emitter.emit("pop rax")
                self.emitter.emit("cmp rax, 1 ; test true")
                self.emitter.emit(f"je {or_true_label}")

                self.emitter.emit("; or evaluated to false")
                self.emitter.emit("push 0")
                self.emitter.emit(f"jmp {or_end_label}")

                self.emitter.emit(f"{or_true_label}:", indent=0)
                self.emitter.emit("push 1")
                self.emitter.emit(f"{or_end_label}:", indent=0)
            elif binary.operator.ttype == TokenType.And:
                and_false_label = self.and_false_label()
                and_end_label = self.and_end_label()

                binary.lhs.accept(self)
                self.emitter.emit("; and lhs")
                self.emitter.emit("pop rax")
                self.emitter.emit("cmp rax, 0 ; test false")
                self.emitter.emit(f"je {and_false_label}")

                binary.rhs.accept(self)
                self.emitter.emit("; and rhs")
                self.emitter.emit("pop rax")
                self.emitter.emit("cmp rax, 0 ; test false")
                self.emitter.emit(f"je {and_false_label}")

                self.emitter.emit("; and evaluated to true")
                self.emitter.emit("push 1")
                self.emitter.emit(f"jmp {and_end_label}")

                self.emitter.emit(f"{and_false_label}:", indent=0)
                self.emitter.emit("push 0")
                self.emitter.emit(f"{and_end_label}:", indent=0)
            else:
                assert False, f"unreachable binary operator: {binary.operator.ttype}"

    def visit_unary(self, unary: Unary) -> None:
        unary.expr.accept(self)
        if unary.operator.ttype == TokenType.Minus:
            self.emitter.emit("; negate (unary)")
            self.emitter.emit("pop rax")
            self.emitter.emit("imul rax, -1")
            self.emitter.emit("push rax")
        elif unary.operator.ttype == TokenType.Not:
            self.emitter.emit("; <not>")
            self.emitter.emit("pop rax")
            self.emitter.emit("cmp rax, 0")
            self.emitter.emit(f"{COMPARISON_SETCC[TokenType.EqualEqual]} al")
            self.emitter.emit("movzx rax, al ; zero-extend AL to RAX")
            self.emitter.emit("push rax")
        elif unary.operator.ttype == TokenType.Plus:
            pass  # Ignore "+"
        else:
            raise CodeGenError(
                f"ERROR: {unary.operator.position}: unsupported unary operator type {unary.operator}"
            )

    def visit_grouping(self, grouping: Grouping) -> None:
        grouping.expr.accept(self)

    def visit_argv(self, argv: Argv) -> None:
        argv.expr.accept(self)

        self.emitter.emit("pop rax")
        self.emitter.emit("imul rax, 8 ; calc offset into argv")

        self.emitter.emit("mov rbx, [__argv] ; addr of ptr to arg[0]")
        self.emitter.emit("add rbx, rax ; addr of ptr to arg[i]")
        self.emitter.emit("mov rdi, [rbx] ; ptr to arg[i]")

        self.emitter.emit("push rdi ; str_len")
        self.emitter.emit("call c_strlen")
        self.emitter.emit("push rax ; str_len")

    def visit_booltrue(self, booltrue: BoolTrue) -> None:
        self.emitter.emit("push 1 ; true")

    def visit_boolfalse(self, boolfalse: BoolFalse) -> None:
        self.emitter.emit("push 0 ; false")

    @contextmanager
    def new_scope(self, is_function: bool = False):
        try:
            old_table = self.symbol_table
            starting_offset = -8 if is_function else self.symbol_table.next_offset
            self.symbol_table = SymbolTable(
                parent=self.symbol_table, next_offset=starting_offset
            )
            yield
        finally:
            self.emitter.emit(
                f"add rsp, {self.symbol_table.reserved_space}; free reserved scope space"
            )
            self.symbol_table = old_table

    def program_prologue(self) -> None:
        self.emitter.emit("global _start", indent=0)
        self.emitter.emit("", indent=0)
        self.emitter.emit("_start:", indent=0)
        self.emitter.emit("; init base pointer")
        self.emitter.emit("mov rbp, rsp")
        self.emitter.emit()
        self.emitter.emit("; save argc and argv into .bss")
        self.emitter.emit("mov rax, [rbp] ")
        self.emitter.emit("mov [__argc], rax")
        self.emitter.emit("lea rax, [rbp+8] ; addr of rbp + 8")
        self.emitter.emit("mov [__argv], rax")
        self.emitter.emit("")

    def program_epilogue(self):
        self.emitter.emit()
        self.emitter.emit("; default exit 0")
        self.emitter.emit("mov rdi, 0")
        self.emitter.emit("call exit")

    def user_defined_fns(self):
        self.emitter.emit()
        self.emitter.emit("; USER FUNCTIONS", indent=0)
        self.emitter.emit()
        for fndef in self.user_fndefs:
            assert len(fndef.params) <= 6, (
                "Functions with more than 6 params (next param on the stack) are currently not supported"
            )

            self.emitter.emit("; arg0 | arg1 | arg2 | arg3 | arg4 | arg5", indent=0)
            self.emitter.emit("; rdi  | rsi  | rdx  | rcx  |  r8  |  r9", indent=0)
            self.emitter.emit(f"{fndef.name.value}:", indent=0)

            self.emitter.emit("; fn prologue")
            self.emitter.emit("push rbp")
            self.emitter.emit("mov rbp, rsp")
            self.emitter.emit()

            reg_order = ["rdi", "rsi", "rdx", "rcx", "r8", "r9"]
            reg_i = 0

            with self.new_scope(is_function=True):
                for param in fndef.params:
                    vartype = VarType.from_token(param.ttype)
                    self.emitter.emit(
                        f"sub rsp, {vartype.size} ; reserve space for param {param.name.value}"
                    )
                    offset = self.symbol_table.define(param.name.value, vartype)

                    if vartype in (VarType.Int, VarType.Bool):
                        assert reg_i <= 5, (
                            "More than 6 registers used (strings take up 2)"
                        )
                        self.emitter.emit(f"mov [rbp{offset:+d}], {reg_order[reg_i]}")
                        reg_i += 1
                    elif vartype == VarType.String:
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
                    else:
                        raise CodeGenError(
                            f"ERROR: {param.name.position}: Unsupported VarType `{vartype}`"
                        )

                self.emitter.emit("; fn body")
                for stmt in fndef.body:
                    stmt.accept(self)

            self.emitter.emit()
            self.emitter.emit(".epilogue:", indent=0)
            self.emitter.emit("mov rsp, rbp")
            self.emitter.emit("pop rbp")
            self.emitter.emit("ret")

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
            self.emitter.emit(f"{label}_len: dq {len(raw_s)}")
            self.emitter.emit(f"{label}: db {encode_nasm_string(raw_s)}")

    def bss_section(self) -> None:
        self.emitter.emit("")
        self.emitter.emit("section .bss", indent=0)
        self.emitter.emit("__argc: resq 1 ; argc")
        self.emitter.emit("__argv: resq 1 ; addr of ptr to argv[0]")
        self.emitter.emit("__itoa_buf: resb 32")

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
