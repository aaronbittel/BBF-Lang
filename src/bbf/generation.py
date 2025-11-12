from __future__ import annotations

from contextlib import contextmanager
from typing import TextIO

from bbf import builtins as bbf_builtins
from bbf.lexer import TokenType
from bbf.parser import (
    NodeExpr,
    NodeExprArgv,
    NodeExprAtoi,
    NodeExprBinary,
    NodeExprGrouping,
    NodeExprIdent,
    NodeExprIntLit,
    NodeExprStringLit,
    NodeExprUnary,
    NodeProgram,
    NodeScope,
    NodeStmt,
    NodeStmtAssign,
    NodeStmtDecl,
    NodeStmtExit,
    NodeStmtFor,
    NodeStmtIf,
    NodeStmtWrite,
)
from bbf.symbol_table import SymbolTable, VarInfo, VarType

COMPARISON_SETCC = {
    TokenType.Less: "setl",  # <
    TokenType.LessEqual: "setle",  # <=
    TokenType.Greater: "setg",  # >
    TokenType.GreaterEqual: "setge",  # >=
    TokenType.EqualEqual: "sete",  # ==
    TokenType.BangEqual: "setne",  # !=
}


class CodeGenerator:
    def __init__(self, prog: NodeProgram) -> None:
        self.prog = prog
        self.emitter = Emitter()

        self.symbol_table = SymbolTable()
        # TODO: move this into symboltable again
        self.symbol_table.offsets = {"argc": VarInfo(offset=0, ttype=VarType.Int)}
        self.strings: list[str] = []
        self.if_label_count = 0
        self.elif_label_count = 0
        self.loop_count = 0
        self.comparison_count = 0

    def write_to(self, file: TextIO) -> None:
        self.emitter.write_to(file)

    def gen_prog(self) -> None:
        self.program_prologue()

        with self.new_scope(self.prog.scope):
            for stmt in self.prog.scope.stmts:
                self.gen_stmt(stmt)
                self.emitter.emit("")

        self.program_epilogue()

        self.builtins()
        self.static_section()
        self.bss_section()

    def gen_stmt(self, stmt: NodeStmt) -> None:
        node_str = str(stmt)
        for line in node_str.split("\n"):
            self.emitter.emit(f"; {line}")
        if isinstance(stmt.stmt, NodeStmtExit):
            self.gen_stmt_exit(stmt.stmt)
        elif isinstance(stmt.stmt, NodeStmtDecl):
            self.gen_stmt_decl(stmt.stmt)
        elif isinstance(stmt.stmt, NodeStmtAssign):
            self.gen_stmt_assign(stmt.stmt)
        elif isinstance(stmt.stmt, NodeStmtIf):
            self.gen_stmt_if(stmt.stmt)
        elif isinstance(stmt.stmt, NodeStmtWrite):
            self.gen_stmt_print(stmt.stmt)
        elif isinstance(stmt.stmt, NodeStmtFor):
            self.gen_stmt_for(stmt.stmt)
        elif isinstance(stmt.stmt, NodeScope):
            self.gen_stmt_scope(stmt.stmt)
        else:
            raise CodeGenError(f"ERROR: unexpected NodeStmt: {stmt}")

    def gen_stmt_exit(self, stmt: NodeStmtExit) -> None:
        expr = stmt.expr
        self.gen_expr(expr)
        self.emitter.emit("pop rdi")
        self.emitter.emit("call __builtin_exit")

    def gen_stmt_decl(self, stmt: NodeStmtDecl) -> None:
        ident, expr = stmt.ident, stmt.expr

        varinfo = self.symbol_table.lookup(ident.value)
        assert varinfo is not None, "`new_scope()` declares all new variables"
        offset = varinfo.offset

        self.gen_expr(expr)
        if stmt.ttype == VarType.Int:
            self.emitter.emit("pop rax")
            self.emitter.emit(f"mov [rbp{offset:+d}], rax")
        elif stmt.ttype == VarType.String:
            self.emitter.emit("pop rdx ; str_len")
            self.emitter.emit("pop rax ; str_ptr")
            self.emitter.emit(f"mov [rbp{offset:+d}], rax ; store str_ptr")
            self.emitter.emit(f"mov [rbp{offset - 8:+d}], rdx ; store str_len")

    def gen_stmt_assign(self, stmt: NodeStmtAssign) -> None:
        ident, expr = stmt.ident, stmt.expr
        self.gen_expr(expr)

        varinfo = self.symbol_table.lookup(ident.value)
        if varinfo is None:
            raise CodeGenError(
                f"ERROR: {ident.position}: undefined variable `{ident.value}`"
            )
        self.emitter.emit("pop rax")
        self.emitter.emit(f"mov [rbp{varinfo.offset:+d}], rax")

    def gen_stmt_if(self, stmt: NodeStmtIf) -> None:
        label_id = self.if_label_count
        self.if_label_count += 1

        end_label = f".end_if_{label_id}_label"
        else_label = f".else_{label_id}_label"

        # --- IF condition ---
        self.gen_expr(stmt.condition)
        self.emitter.emit("pop rax")
        self.emitter.emit("cmp rax, 0")
        next_label = end_label
        if len(stmt.elifs) > 0:
            next_label = f".elif_{label_id}_0_label"
        elif stmt.else_scope is not None:
            next_label = else_label
        self.emitter.emit(f"je {next_label}")

        # --- IF block ---
        with self.new_scope(stmt.scope):
            for s in stmt.scope.stmts:
                self.gen_stmt(s)
        self.emitter.emit(f"jmp {end_label}")

        # --- ELIF chain ---
        if len(stmt.elifs) > 0:
            for i, elif_block in enumerate(stmt.elifs):
                this_label = f".elif_{label_id}_{i}_label: ; THIS LABEL"
                next_label = end_label
                if i + 1 < len(stmt.elifs):  # there is a next elif block
                    next_label = f".elif_{label_id}_{i + 1}_label ; NEXT LABEL"
                elif stmt.else_scope is not None:  # there is a else block
                    next_label = else_label
                self.emitter.emit(this_label, indent=0)
                self.gen_expr(elif_block.condition)
                self.emitter.emit("pop rax")
                self.emitter.emit("cmp rax, 0")
                self.emitter.emit(f"je {next_label}")
                with self.new_scope(elif_block.scope):
                    for s in elif_block.scope.stmts:
                        self.gen_stmt(s)
                self.emitter.emit(f"jmp {end_label}")
                # self.emitter.emit(f"{next_label}:", indent=0)

        # --- ELSE block ---
        self.emitter.emit(f"{else_label}:", indent=0)
        if stmt.else_scope:
            with self.new_scope(stmt.else_scope):
                for s in stmt.else_scope.stmts:
                    self.gen_stmt(s)

        # --- END ---
        self.emitter.emit(f"{end_label}:", indent=0)

    @contextmanager
    def new_scope(self, scope: NodeScope):
        try:
            old_table = self.symbol_table
            self.symbol_table = SymbolTable(
                parent=self.symbol_table, next_offset=self.symbol_table.next_offset
            )
            total = 0
            for stmt in scope.stmts:
                if isinstance(stmt.stmt, NodeStmtDecl):
                    decl = stmt.stmt
                    self.symbol_table.define(decl.ident.value, decl.ttype)
                    print(f"defining {decl.ident.value}", self.symbol_table.offsets)
                    total += decl.ttype.value
            self.emitter.emit(f"sub rsp, {total} ; reserve space for scope")
            yield
        finally:
            self.symbol_table = old_table
            self.emitter.emit(f"add rsp, {total} ; free space after scope")

    def gen_stmt_for(self, stmt: NodeStmtFor) -> None:
        # NOTE: currently for loops just declare a variable that will not be cleaned up after the loop
        loop_ident, range_expr, scope = stmt.loop_ident, stmt.range_expr, stmt.scope
        with self.new_scope(stmt.scope):
            # NOTE: loop var is a new variable scoped to the loop scope
            loop_ident_offset = self.symbol_table.define(
                loop_ident.value, ttype=VarType.Int
            )
            # TODO: check that range_expr.start is actually an Int
            self.gen_expr(range_expr.start)
            self.emitter.emit("pop rax ; loop var")
            self.emitter.emit(
                f"sub rsp, {VarType.Int.value} ; reserve space for loop var"
            )
            self.emitter.emit(f"mov [rbp{loop_ident_offset:+d}], rax")
            self.emitter.emit(f"loop_{self.loop_count}_start:", indent=0)
            for s in scope.stmts:
                self.gen_stmt(s)
            range_ident = self.symbol_table.lookup(loop_ident.value)
            assert range_ident is not None, f"{loop_ident.value} was just created"
            self.emitter.emit(
                f"inc qword [rbp{range_ident.offset:+d}] ; increment loop variable"
            )
            self.gen_expr(range_expr.end)
            self.emitter.emit("pop rax ; range end")
            self.emitter.emit(
                f"cmp qword [rbp{range_ident.offset:+d}], rax ; check if condition"
            )
            if range_expr.inclusive:
                self.emitter.emit(f"jle loop_{self.loop_count}_start")
            else:
                self.emitter.emit(f"jl loop_{self.loop_count}_start")
            self.loop_count += 1

    def gen_stmt_scope(self, scope: NodeScope) -> None:
        with self.new_scope(scope):
            for stmt in scope.stmts:
                self.gen_stmt(stmt)

    def gen_stmt_print(self, stmt: NodeStmtWrite) -> None:
        self.gen_expr_as_string(stmt.expr)
        self.emitter.emit("pop rdx ; str_len")
        self.emitter.emit("pop rsi ; str_ptr")
        self.emitter.emit(f"mov rdi, {stmt.fd} ; fd")
        self.emitter.emit("call __builtin_write")

    # TODO: Make gen_stmt_* functions return values or registers
    # When you add binary expressions or function calls, you’ll want to evaluate
    # subexpressions into registers or stack locations.
    def gen_expr(self, expr: NodeExpr) -> None:
        """Generate code for an expression.

        Always pushes the results onto the stack.
        """
        if isinstance(expr.var, NodeExprIntLit):
            self.gen_node_expr_intlit(expr.var)
        elif isinstance(expr.var, NodeExprIdent):
            self.gen_node_expr_ident(expr.var)
        elif isinstance(expr.var, NodeExprBinary):
            self.gen_node_expr_binary(expr.var)
        elif isinstance(expr.var, NodeExprUnary):
            self.gen_node_expr_unary(expr.var)
        elif isinstance(expr.var, NodeExprGrouping):
            self.gen_expr(expr.var.expr)
        elif isinstance(expr.var, NodeExprStringLit):
            self.gen_node_expr_stringlit(expr.var)
        elif isinstance(expr.var, NodeExprArgv):
            self.gen_node_expr_argv(expr.var)
        elif isinstance(expr.var, NodeExprAtoi):
            self.gen_node_expr_atoi(expr.var)
        else:
            assert False, f"unreachable: {expr.var}"

    def gen_expr_as_string(self, expr: NodeExpr) -> None:
        self.gen_expr(expr)
        if isinstance(expr.var, NodeExprStringLit) or isinstance(
            expr.var, NodeExprArgv
        ):
            return

        if isinstance(expr.var, NodeExprIdent):
            ident = expr.var
            varinfo = self.symbol_table.lookup(ident.token.value)
            if varinfo is None:
                raise CodeGenError(
                    f"ERROR: {ident.token.position}: undeclared identifier {ident.token.value}"
                )
            if varinfo.ttype == VarType.String:
                return

        self.emitter.emit("pop rdi")
        self.emitter.emit("call __builtin_itoa")
        self.emitter.emit("push rax ; str_ptr")
        self.emitter.emit("push rdx ; str_len")

    def gen_node_expr_intlit(self, intlit: NodeExprIntLit) -> None:
        # NOTE: What to do when value already exists?
        self.emitter.emit(f"mov rax, {intlit.token.value}")
        self.emitter.emit("push rax")

    def gen_node_expr_ident(self, ident: NodeExprIdent) -> None:
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
        if varinfo.ttype == VarType.Int:
            self.emitter.emit(
                f"push qword [rbp{varinfo.offset:+d}] ; push value from variable {ident.token.value}"
            )
        elif varinfo.ttype == VarType.String:
            self.emitter.emit(
                f"push qword [rbp{varinfo.offset:+d}] ; str_ptr form variable {ident.token.value}"
            )
            self.emitter.emit(
                f"push qword [rbp{varinfo.offset - 8:+d}] ; str_len form variable {ident.token.value}"
            )
        else:
            assert False, f"unreachable: unknown VarType: {varinfo.ttype}"

    def gen_node_expr_binary(self, binary: NodeExprBinary) -> None:
        self.gen_expr(binary.lhs)
        self.gen_expr(binary.rhs)
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
            assert False, f"unreachable {binary.operator.ttype}"

    def gen_node_expr_unary(self, unary: NodeExprUnary) -> None:
        self.gen_expr(unary.expr)
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

    def gen_node_expr_stringlit(self, stringlit: NodeExprStringLit) -> None:
        self.strings.append(stringlit.token.value)
        label = make_string_label(len(self.strings) - 1)
        len_label = f"{label}_len"
        self.emitter.emit("; load string literal")
        self.emitter.emit("; push string addr")
        self.emitter.emit(f"lea rax, [{label}]")
        self.emitter.emit("push rax")
        self.emitter.emit("; push string length")
        self.emitter.emit(f"push qword [{len_label}]")

    def gen_node_expr_argv(self, argv: NodeExprArgv) -> None:
        self.gen_expr(argv.expr)

        self.emitter.emit("pop rax")
        self.emitter.emit("imul rax, 8 ; calc offset into argv")
        self.emitter.emit("lea rbx, [rbp + rax + 8] ; +8 to skip argc")
        self.emitter.emit("mov rdi, [rbx]")

        self.emitter.emit("push rdi ; str_len")
        self.emitter.emit("call __builtin_c_strlen")
        self.emitter.emit("push rax ; str_len")

    def gen_node_expr_atoi(self, atoi: NodeExprAtoi) -> None:
        self.gen_expr(atoi.expr)
        # NOTE: This will break if expression does not evaluate to a string
        self.emitter.emit("pop rsi ; str_len")
        self.emitter.emit("pop rdi ; str_ptr")
        self.emitter.emit("call __builtin_atoi")
        self.emitter.emit("push rax")

    def program_prologue(self) -> None:
        self.emitter.emit("global _start", indent=0)
        self.emitter.emit("", indent=0)
        self.emitter.emit("_start:", indent=0)
        self.emitter.emit("; init base pointer")
        self.emitter.emit("mov rbp, rsp")
        self.emitter.emit("")

    def program_epilogue(self):
        self.emitter.emit("; default exit 0")
        self.emitter.emit("mov rdi, 0")
        self.emitter.emit("call __builtin_exit")

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
        for i, raw_s in enumerate(self.strings):
            label = make_string_label(i)
            self.emitter.emit(f"{label}_len: dq {len(raw_s)}")
            self.emitter.emit(f"{label}: db {encode_nasm_string(raw_s)}")

    def bss_section(self) -> None:
        self.emitter.emit("")
        self.emitter.emit("section .bss", indent=0)
        self.emitter.emit("__itoa_buf: resb 32")


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


class Emitter:
    def __init__(self):
        self.lines: list[str] = []

    def emit(self, line: str = "", indent: int = 4) -> None:
        self.lines.append(" " * indent + line)

    def write_to(self, file: TextIO) -> None:
        file.write("\n".join(self.lines))

    def multi(self, code: str) -> None:
        for line in code.split("\n"):
            self.lines.append(line)
