from __future__ import annotations

from typing import TextIO

from bbf.builtins import (
    _builtin_atoi,
    _builtin_exit,
    _builtin_itoa,
    _builtin_print,
    _builtin_write,
)
from bbf.lexer import TokenType
from bbf.parser import (
    NodeExpr,
    NodeExprBinary,
    NodeExprGrouping,
    NodeExprIdent,
    NodeExprIntLit,
    NodeExprStringLit,
    NodeExprUnary,
    NodeProgram,
    NodeStmt,
    NodeStmtAssign,
    NodeStmtExit,
    NodeStmtPrint,
)


class CodeGenerator:
    def __init__(self, prog: NodeProgram) -> None:
        self.prog = prog
        self.emitter = Emitter()

        self.symbols = SymbolTable()
        self.strings: list[str] = []

    def write_to(self, file: TextIO) -> None:
        self.emitter.write_to(file)

    def gen_prog(self) -> None:
        self.program_prologue()

        for stmt in self.prog.stmts:
            self.gen_stmt_node(stmt)
            self.emitter.emit("")

        self.program_epilogue()

        self.builtins()
        self.static_section()
        self.bss_section()

    def gen_stmt_node(self, node_stmt: NodeStmt) -> None:
        self.emitter.emit(f"; {node_stmt}")
        if isinstance(node_stmt.stmt, NodeStmtExit):
            self.gen_stmt_exit(node_stmt.stmt)
        elif isinstance(node_stmt.stmt, NodeStmtAssign):
            self.gen_stmt_assign(node_stmt.stmt)
        elif isinstance(node_stmt.stmt, NodeStmtPrint):
            self.gen_stmt_print(node_stmt.stmt)
        else:
            raise CodeGenError(f"ERROR: unexpected NodeStmt: {node_stmt}")

    def gen_stmt_exit(self, stmt: NodeStmtExit) -> None:
        expr = stmt.expr
        self.gen_expr(expr)
        self.emitter.emit("pop rdi")
        self.emitter.emit("call __builtin_exit")

    def gen_stmt_assign(self, stmt: NodeStmtAssign) -> None:
        leftside_ident, expr = stmt.ident, stmt.expr
        self.gen_expr(expr)  # right side value is on the stack

        leftside_offset = self.symbols.lookup(leftside_ident.value)
        if leftside_offset is None:
            # definition of new variable
            self.symbols.define(leftside_ident.value)
        else:
            # redefining value of variable
            self.emitter.emit(f"; redefining of variable {leftside_ident.value}")
            self.emitter.emit("pop rax")
            self.emitter.emit(f"mov [rbp-{leftside_offset}], rax")

    def gen_stmt_print(self, stmt: NodeStmtPrint) -> None:
        if isinstance(stmt.expr.var, NodeExprStringLit):
            self.gen_expr(stmt.expr)  # length, str-addr on stack
            self.emitter.emit("pop rdx ; move length into rdx")
            self.emitter.emit("pop rsi ; move str-addr into rsi")
            self.emitter.emit("call __builtin_print")
        elif (
            isinstance(stmt.expr.var, NodeExprIntLit)
            or isinstance(stmt.expr.var, NodeExprUnary)
            or isinstance(stmt.expr.var, NodeExprIdent)
            or isinstance(stmt.expr.var, NodeExprBinary)
        ):
            self.gen_expr(stmt.expr)  # literal on stack
            self.emitter.emit("pop rdi")
            self.emitter.emit("call __builtin_itoa")
            self.emitter.emit("mov rdi, rax")
            self.emitter.emit("mov rsi, rdx")
            self.emitter.emit("call __builtin_write")
        else:
            assert False, f"not implemented: {stmt.expr.var}, {type(stmt.expr.var)}"

    # TODO: Make gen_stmt_* functions return values or registers
    # When you add binary expressions or function calls, you’ll want to evaluate
    # subexpressions into registers or stack locations.
    def gen_expr(self, expr: NodeExpr) -> None:
        """Generate code for an expression.

        Always moves the result onto the stack.
        """
        if isinstance(expr.var, NodeExprIntLit):
            # NOTE: What to do when value already exists?
            int_lit = expr.var.token
            self.emitter.emit(f"mov rax, {int_lit.value}; pushing {int_lit.value}")
            self.emitter.emit("push rax")
        elif isinstance(expr.var, NodeExprIdent):
            ident = expr.var.ident
            offset = self.symbols.lookup(ident.value)
            if offset is None:
                raise CodeGenError(
                    f"ERROR: {ident.position}: identifier `{ident.value}` was not defined"
                )
            self.emitter.emit(
                f"push qword [rbp-{offset}] ; push value from variable {ident.value}"
            )
        elif isinstance(expr.var, NodeExprBinary):
            binary = expr.var
            self.gen_expr(expr.var.lhs)
            self.gen_expr(expr.var.rhs)
            self.emitter.emit("pop rbx; pop rhs ?")
            self.emitter.emit("pop rax; pop lhs ?")
            if binary.operator.ttype == TokenType.Plus:
                self.emitter.emit("; addition")
                self.emitter.emit("add rax, rbx")
                self.emitter.emit("push rax; push result")
            elif binary.operator.ttype == TokenType.Minus:
                self.emitter.emit("; subtraction")
                self.emitter.emit("sub rax, rbx")
                self.emitter.emit("push rax; push result")
            elif binary.operator.ttype == TokenType.Star:
                self.emitter.emit("; multiplication")
                self.emitter.emit("imul rbx")
                self.emitter.emit("push rax; push result")
            elif binary.operator.ttype == TokenType.Slash:
                self.emitter.emit("; division")
                self.emitter.emit(
                    "xor rdx, rdx ; clear upper 64bit of 128 bit division"
                )
                self.emitter.emit("div rbx")
                self.emitter.emit("push rax; push result")
            elif binary.operator.ttype == TokenType.Percent:
                self.emitter.emit("; modulo")
                self.emitter.emit(
                    "xor rdx, rdx ; clear upper 64bit of 128 bit division"
                )
                self.emitter.emit("div rbx")
                self.emitter.emit("push rdx; push result (remainder always in rdx)")
            else:
                assert False, f"unreachable {binary.operator.ttype}"
        elif isinstance(expr.var, NodeExprUnary):
            unary = expr.var
            assert unary.operator.ttype == TokenType.Minus
            assert isinstance(unary.right.var, NodeExprIntLit)
            int_lit = unary.right.var.token
            self.emitter.emit(f"mov rax, {unary.operator.value}{int_lit.value}")
            self.emitter.emit("push rax")
        elif isinstance(expr.var, NodeExprGrouping):
            self.gen_expr(expr.var.expr)
        elif isinstance(expr.var, NodeExprStringLit):
            self.strings.append(expr.var.token.value)
            label = make_string_label(len(self.strings) - 1)
            len_label = f"{label}_len"
            self.emitter.emit("; load string literal")
            self.emitter.emit("; push string addr")
            self.emitter.emit(f"lea rax, [{label}]")
            self.emitter.emit("push rax")
            self.emitter.emit("; push string length")
            self.emitter.emit(f"push qword [{len_label}]")
        else:
            assert False, f"unreachable: {expr.var}"

    def program_prologue(self) -> None:
        self.emitter.emit("global _start", indent=0)
        self.emitter.emit("", indent=0)
        self.emitter.emit("_start:", indent=0)
        self.emitter.emit("; init base pointer")
        self.emitter.emit("push rbp")
        self.emitter.emit("mov rbp, rsp")
        self.emitter.emit("")

    def program_epilogue(self):
        self.emitter.emit("; default exit 0")
        self.emitter.emit("mov rdi, 0")
        self.emitter.emit("call __builtin_exit")

    def builtins(self) -> None:
        self.emitter.emit("")
        self.emitter.emit("; BUILTIN FUNCTIONS", indent=0)

        self.emitter.multi(_builtin_exit)
        self.emitter.multi(_builtin_print)
        self.emitter.multi(_builtin_atoi)
        self.emitter.multi(_builtin_itoa)
        self.emitter.multi(_builtin_write)

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

    output = '"'
    for i, ch in enumerate(string):
        if ch == "\n":
            output += _insert_escaped_code(i=i, code=10)
        elif ch == "\t":
            output += _insert_escaped_code(i=i, code=9)
        else:
            output += ch
    return output + '"'


def make_string_label(i: int) -> str:
    return f"s_lit_{i:02}"


class CodeGenError(Exception):
    pass


class SymbolTable:
    def __init__(self):
        self.offsets: dict[str, int] = {}
        self.next_offset = 8

    def define(self, name: str) -> int:
        offset = self.next_offset
        self.offsets[name] = offset
        self.next_offset += 8
        return offset

    def lookup(self, name: str) -> int | None:
        return self.offsets.get(name)


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
