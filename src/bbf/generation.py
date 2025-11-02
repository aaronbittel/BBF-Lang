from __future__ import annotations

from typing import TextIO

from bbf.lexer import TokenType
from bbf.parser import (
    NodeExpr,
    NodeExprBinary,
    NodeExprGrouping,
    NodeExprIdent,
    NodeExprIntLit,
    NodeExprUnary,
    NodeProgram,
    NodeStmt,
    NodeStmtAssign,
    NodeStmtExit,
)


class CodeGenerator:
    def __init__(self, prog: NodeProgram) -> None:
        self.prog = prog
        self.emitter = Emitter()

        self.symbols = SymbolTable()

    def write_to(self, file: TextIO) -> None:
        self.emitter.write_to(file)

    def gen_prog(self) -> None:
        self.program_prologue()

        for stmt in self.prog.stmts:
            self.gen_stmt_node(stmt)
            self.emitter.emit("")

        self.program_epilogue()

        self.gen_builtins()

    def gen_stmt_node(self, node_stmt: NodeStmt) -> None:
        # stmt: NodeStmtExit | NodeStmtAssign
        if isinstance(node_stmt.stmt, NodeStmtExit):
            self.gen_stmt_exit(node_stmt.stmt)
        elif isinstance(node_stmt.stmt, NodeStmtAssign):
            self.gen_stmt_assign(node_stmt.stmt)
        else:
            raise CodeGenError(f"ERROR: unexpected NodeStmt: {node_stmt}")

    def gen_stmt_exit(self, stmt: NodeStmtExit) -> None:
        expr = stmt.expr
        self.emitter.emit(f"; {stmt}")
        self.gen_expr(expr)
        self.emitter.emit("pop rdi")
        self.emitter.emit("call __builtin_exit")

    def gen_stmt_assign(self, stmt: NodeStmtAssign) -> None:
        leftside_ident, expr = stmt.ident, stmt.expr
        self.emitter.emit(f"; {stmt}")
        self.gen_expr(expr)  # right side value is in `rax`

        leftside_offset = self.symbols.lookup(leftside_ident.value)
        if leftside_offset is None:
            # definition of new variable
            self.symbols.define(leftside_ident.value)
        else:
            # redefining value of variable
            self.emitter.emit(f"mov [rbp-{leftside_offset}], rax")

    # TODO: Make gen_stmt_* functions return values or registers
    # When you add binary expressions or function calls, you’ll want to evaluate
    # subexpressions into registers or stack locations.
    def gen_expr(self, expr: NodeExpr) -> None:
        """Generate code for an expression.

        Always moves the result onto the stack.
        """
        if isinstance(expr.var, NodeExprIntLit):
            # NOTE: What to do when value already exists?
            int_lit = expr.var.int_lit
            self.emitter.emit(f"push {int_lit.value}; pushing {int_lit.value}")
        elif isinstance(expr.var, NodeExprIdent):
            ident = expr.var.ident
            offset = self.symbols.lookup(ident.value)
            if offset is None:
                raise CodeGenError(
                    f"ERROR: {ident.position}: identifier `{ident.value}` was not defined"
                )
            self.emitter.emit(
                f"push QWORD [rbp-{offset}] ; push value from variable {ident.value}"
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
            int_lit = unary.right.var.int_lit
            self.emitter.emit(f"push {unary.operator.value}{int_lit.value}")
        elif isinstance(expr.var, NodeExprGrouping):
            self.gen_expr(expr.var.expr)
        else:
            assert False, f"unreachable: {expr.var}"
            # self.emitter.emit(f"mov rax, {binary.lhs.var}")
        # elif isinstance(expr.var, NodeExprAdd):
        #     left, right = expr.var.lhs, expr.var.rhs
        #     self.gen_expr(right)
        #     self.emitter.emit("push rax ; save RHS on stack")
        #     self.gen_expr(left)
        #     self.emitter.emit("pop rbx ; restore RHS into rbx")
        #     self.emitter.emit("add rax, rbx")
        # elif isinstance(expr.var, NodeExprSub):
        # left, right = expr.var.lhs, expr.var.rhs
        # self.gen_expr(right)
        # self.emitter.emit("push rax ; save RHS on stack")
        # self.gen_expr(left)
        # self.emitter.emit("pop rbx ; restore RHS into rbx")
        # self.emitter.emit("sub rax, rbx")  # rax = rax - rbx
        # else:
        #     assert False, "unreachable"

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

    def gen_builtins(self) -> None:
        self.emitter.emit("")
        self.emitter.emit("; BUILTIN FUNCTIONS", indent=0)
        self.emitter.emit("__builtin_exit:", indent=0)
        self.emitter.emit("mov rax, 60")
        self.emitter.emit("syscall")


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
