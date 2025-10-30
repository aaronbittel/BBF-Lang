from pathlib import Path
import sys
from bbf.parser import (
    NodeExpr,
    NodeExprIdent,
    NodeExprIntLit,
    NodeProgram,
    NodeStmt,
    NodeStmtAssign,
    NodeStmtExit,
)
from bbf.utils import eprint


class CodeGenerator:
    def __init__(self, prog: NodeProgram, output_path: Path) -> None:
        self.prog = prog
        self.output_path = output_path
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        self._locals: dict[str, int] = {}  # name => offset
        self._next_offset = 8
        self._file = self.output_path.open(mode="w")

    def gen_prog(self) -> None:
        try:
            self._file.write("global _start\n")
            self._file.write("_start:\n")
            self._file.write("    ; init base pointer\n\n")
            self._file.write("    push rbp\n")
            self._file.write("    mov rbp, rsp\n")

            for stmt in self.prog.stmts:
                self.gen_stmt_node(stmt)

            # deself._fileault exit 0 if no explicit exit call
            self._file.write("\n")
            self._file.write("; default exit 0\n")
            self._file.write("    mov rdi, 0\n")
            self._file.write("    call __bulitin_exit\n")

            self._file.write("\n")
            self._file.write("; BUILTIN FUNCTIONS\n")
            self._file.write("__bulitin_exit:\n")
            self._file.write("    mov rax, 60\n")
            self._file.write("    syscall\n")
        finally:
            self._file.close()

    def gen_stmt_node(self, node_stmt: NodeStmt) -> None:
        # stmt: NodeStmtExit | NodeStmtAssign
        if isinstance(node_stmt.stmt, NodeStmtExit):
            self.gen_stmt_exit(node_stmt.stmt)
        elif isinstance(node_stmt.stmt, NodeStmtAssign):
            self.gen_stmt_assign(node_stmt.stmt)
        else:
            eprint(f"ERROR: unexpected NodeStmt: {node_stmt}")
            sys.exit(1)

    def gen_stmt_exit(self, stmt: NodeStmtExit) -> None:
        expr = stmt.expr
        self._file.write(f"    ; {stmt}\n")
        self.gen_expr(expr)
        self._file.write("    mov rdi, rax\n")
        self._file.write("    call __bulitin_exit\n")

    def gen_stmt_assign(self, stmt: NodeStmtAssign) -> None:
        leftside_ident, expr = stmt.ident, stmt.expr
        self._file.write(f"    ; NodeStmtAssign: {stmt}\n")
        self.gen_expr(expr)  # right side value is in `rax`

        leftside_offset = self._locals.get(leftside_ident.value)
        if leftside_offset is None:
            # definition of new variable
            self._locals[leftside_ident.value] = self._next_offset
            self._next_offset += 8
            self._file.write("    push rax\n")
        else:
            # redefining value of variable
            self._file.write(f"    mov [rbp-{leftside_offset}], rax\n")

    def gen_expr(self, expr: NodeExpr) -> None:
        """Generate code for an expression.

        Always moves the result onto `rax`.
        """
        if isinstance(expr.var, NodeExprIntLit):
            # NOTE: What to do when value already exists?
            int_lit = expr.var.int_lit
            self._file.write(f"    mov rax, {int_lit.value}\n")
        elif isinstance(expr.var, NodeExprIdent):
            ident = expr.var.ident
            offset = self._locals.get(ident.value)
            if offset is None:
                eprint(
                    f"ERROR: {ident.position}: identifier `{ident.value}` was not defined"
                )
                sys.exit(1)
            self._file.write(
                f"    mov rax, [rbp-{offset}]; retrieve value from variable {ident.value}\n"
            )
