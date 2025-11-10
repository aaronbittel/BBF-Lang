from __future__ import annotations

from typing import TextIO

from bbf import builtins as bbf_builtins
from bbf.lexer import Token, TokenType
from bbf.parser import (
    NodeExpr,
    NodeExprArgv,
    NodeExprBinary,
    NodeExprGrouping,
    NodeExprIdent,
    NodeExprIntLit,
    NodeExprStringLit,
    NodeExprUnary,
    NodeProgram,
    NodeStmt,
    NodeStmtAssign,
    NodeStmtDecl,
    NodeStmtExit,
    NodeStmtFor,
    NodeStmtIf,
    NodeStmtPrint,
)
from bbf.symbol_table import SymbolTable, VarType


class CodeGenerator:
    def __init__(self, prog: NodeProgram) -> None:
        self.prog = prog
        self.emitter = Emitter()

        self.symbol_table = SymbolTable()
        self.strings: list[str] = []
        self.if_label_count = 0
        self.elif_label_count = 0
        self.loop_count = 0

    def write_to(self, file: TextIO) -> None:
        self.emitter.write_to(file)

    def gen_prog(self) -> None:
        self.program_prologue()

        for stmt in self.prog.stmts:
            self.gen_stmt(stmt)
            self.emitter.emit("")

        self.program_epilogue()

        self.builtins()
        self.static_section()
        self.bss_section()

    def gen_stmt(self, stmt: NodeStmt) -> None:
        node_str = str(stmt)
        for l in node_str.split("\n"):
            self.emitter.emit(f"; {l}")
        if isinstance(stmt.stmt, NodeStmtExit):
            self.gen_stmt_exit(stmt.stmt)
        elif isinstance(stmt.stmt, NodeStmtDecl):
            self.gen_stmt_decl(stmt.stmt)
        elif isinstance(stmt.stmt, NodeStmtAssign):
            self.gen_stmt_assign(stmt.stmt)
        elif isinstance(stmt.stmt, NodeStmtIf):
            self.gen_stmt_if(stmt.stmt)
        elif isinstance(stmt.stmt, NodeStmtPrint):
            self.gen_stmt_print(stmt.stmt)
        elif isinstance(stmt.stmt, NodeStmtFor):
            self.gen_stmt_for(stmt.stmt)
        else:
            raise CodeGenError(f"ERROR: unexpected NodeStmt: {stmt}")

    def gen_stmt_exit(self, stmt: NodeStmtExit) -> None:
        expr = stmt.expr
        self.gen_expr(expr)
        self.emitter.emit("pop rdi")
        self.emitter.emit("call __builtin_exit")

    def gen_stmt_decl(self, stmt: NodeStmtDecl) -> None:
        ident, expr = stmt.ident, stmt.expr
        self.gen_expr(expr)  # right side value is on the stack

        varinfo = self.symbol_table.lookup(ident.value)
        if varinfo is None:
            # definition of new variable
            self.symbol_table.define(ident.value, ttype=stmt.ttype)
            return
        # NOTE: for now don't allow redefining of variables
        # TODO: should be allowed later again
        raise CodeGenError(
            f"WIP: Redefinition of variables is currently not supported ({ident})"
        )

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
        var = stmt.condition.var
        if isinstance(var, NodeExprIntLit):
            token = var.token
            self.emitter.emit(f"mov rax, {token.value}")
            self.emitter.emit("cmp rax, 0")
            self.emitter.emit(f"je .if_{self.if_label_count}_label")
        elif isinstance(var, NodeExprBinary):
            self.gen_expr(var.lhs)
            self.gen_expr(var.rhs)
            self.emitter.emit("pop rbx ; rhs")
            self.emitter.emit("pop rax ; lhs")
            self.emitter.emit("cmp rax, rbx")
            if var.operator.ttype == TokenType.Greater:
                self.emitter.emit(f"jle .if_{self.if_label_count}_label")
            elif var.operator.ttype == TokenType.GreaterEqual:
                self.emitter.emit(f"jl .if_{self.if_label_count}_label")
            elif var.operator.ttype == TokenType.Less:
                self.emitter.emit(f"jge .if_{self.if_label_count}_label")
            elif var.operator.ttype == TokenType.LessEqual:
                self.emitter.emit(f"jg .if_{self.if_label_count}_label")
            elif var.operator.ttype == TokenType.EqualEqual:
                self.emitter.emit(f"jne .if_{self.if_label_count}_label")
            elif var.operator.ttype == TokenType.BangEqual:
                self.emitter.emit(f"je .if_{self.if_label_count}_label")
            else:
                assert False, (
                    f"`gen_stmt_if`: operator f`{var.operator}` is not supported"
                )
        else:
            assert False, f"`gen_stmt_if`: not implemented for {var} {type(var)}"
        for s in stmt.if_stmts:
            self.gen_stmt(s)
        if stmt.else_stmts is not None:
            self.emitter.emit(f"jmp .end_{self.if_label_count}_label ; skip else-block")
        self.emitter.emit(f".if_{self.if_label_count}_label:", indent=0)
        if stmt.elifs is not None:
            for el in stmt.elifs:
                self.emitter.emit("; -- insert condition for elif --")
                elif_var = el.condition.var
                if isinstance(elif_var, NodeExprIntLit):
                    token = elif_var.token
                    self.emitter.emit(f"mov rax, {token.value}")
                    self.emitter.emit("cmp rax, 0")
                    self.emitter.emit(f"je .if_{self.if_label_count}_label")
                elif isinstance(elif_var, NodeExprBinary):
                    self.gen_expr(elif_var.lhs)
                    self.gen_expr(elif_var.rhs)
                    self.emitter.emit("pop rbx ; rhs")
                    self.emitter.emit("pop rax ; lhs")
                    self.emitter.emit("cmp rax, rbx")
                    if elif_var.operator.ttype == TokenType.Greater:
                        self.emitter.emit(
                            f"jle .elif_{self.if_label_count}{self.elif_label_count}_label"
                        )
                    elif elif_var.operator.ttype == TokenType.GreaterEqual:
                        self.emitter.emit(
                            f"jl .elif_{self.if_label_count}{self.elif_label_count}_label"
                        )
                    elif elif_var.operator.ttype == TokenType.Less:
                        self.emitter.emit(
                            f"jge .elif_{self.if_label_count}{self.elif_label_count}_label"
                        )
                    elif elif_var.operator.ttype == TokenType.LessEqual:
                        self.emitter.emit(
                            f"jg .elif_{self.if_label_count}{self.elif_label_count}_label"
                        )
                    elif elif_var.operator.ttype == TokenType.EqualEqual:
                        self.emitter.emit(
                            f"jne .elif_{self.if_label_count}{self.elif_label_count}_label"
                        )
                    elif elif_var.operator.ttype == TokenType.BangEqual:
                        self.emitter.emit(
                            f"je .elif_{self.if_label_count}{self.elif_label_count}_label"
                        )
                    else:
                        assert False, (
                            f"`gen_stmt_if`: operator f`{elif_var.operator}` is not supported"
                        )
                else:
                    assert False, (
                        f"`gen_stmt_if`: not implemented for {elif_var} {type(elif_var)}"
                    )
                for s in el.stmts:
                    self.gen_stmt(s)
                self.emitter.emit(f"jmp .end_{self.if_label_count}_label")
                self.emitter.emit(
                    f".elif_{self.if_label_count}{self.elif_label_count}_label:"
                )
                self.elif_label_count += 1
                self.emitter.emit("; -- end elif block --")
        if stmt.else_stmts is not None:
            for s in stmt.else_stmts:
                self.gen_stmt(s)
        self.emitter.emit(f".end_{self.if_label_count}_label:", indent=0)
        self.if_label_count += 1
        self.elif_label_count = 0

    def gen_stmt_for(self, stmt: NodeStmtFor) -> None:
        # NOTE: currently for loops just declare a variable that will not be cleaned up after the loop
        loop_ident, range_expr, stmts = stmt.loop_ident, stmt.range_expr, stmt.stmts
        varinfo = self.symbol_table.lookup(loop_ident.value)
        # TODO: move this into seperate type checking section
        if varinfo is not None and varinfo.ttype != VarType.Int:
            raise CodeGenError(
                f"Loop variable must be of type `Int`, not `{varinfo.ttype}`"
            )
        self.symbol_table.define(loop_ident.value, ttype=VarType.Int)
        self.gen_expr(range_expr.start)
        self.emitter.emit(f"loop_{self.loop_count}_start:", indent=0)
        for s in stmts:
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

    # TODO: in grammar: print ( Expression ) -> so just self.gen_expr()
    # but how do I know if String or Int ? -> somehow get expression result type?
    def gen_stmt_print(self, stmt: NodeStmtPrint) -> None:
        if isinstance(stmt.expr.var, NodeExprStringLit):
            self.gen_expr(stmt.expr)  # length, str-addr on stack
            self.emitter.emit("pop rdx ; move length into rdx")
            self.emitter.emit("pop rsi ; move str-addr into rsi")
            self.emitter.emit("call __builtin_print")
        # TODO: how to handle Unary, Binary in print with types?
        elif (
            isinstance(stmt.expr.var, NodeExprIntLit)
            or isinstance(stmt.expr.var, NodeExprUnary)
            or isinstance(stmt.expr.var, NodeExprBinary)
        ):
            self.gen_expr(stmt.expr)  # literal on stack
            self.emitter.emit("pop rdi")
            self.emitter.emit("call __builtin_itoa")
            self.emitter.emit("mov rdi, rax")
            self.emitter.emit("mov rsi, rdx")
            self.emitter.emit("call __builtin_write")
        elif isinstance(stmt.expr.var, NodeExprIdent):
            ident = stmt.expr.var.ident
            varinfo = self.symbol_table.lookup(ident.value)
            if varinfo is None:
                raise CodeGenError(
                    f"ERROR: {ident.position}: undeclared identifier {ident.value}"
                )
            if varinfo.ttype == VarType.Int:
                self.gen_expr(stmt.expr)  # literal on stack
                self.emitter.emit("pop rdi")
                self.emitter.emit("call __builtin_itoa")
                self.emitter.emit("mov rdi, rax")
                self.emitter.emit("mov rsi, rdx")
                self.emitter.emit("call __builtin_write")
            elif varinfo.ttype == VarType.String:
                ptr_offset = varinfo.offset
                len_offset = varinfo.offset + 8
                self.emitter.emit(f"mov rdi, [rbp{ptr_offset:+d}] ; load str ptr")
                self.emitter.emit(f"mov rsi, [rbp{len_offset:+d}] ; load str len")
                self.emitter.emit("call __builtin_write")
        elif isinstance(stmt.expr.var, NodeExprArgv):
            expr = stmt.expr.var.expr
            self.gen_expr(expr)

            self.emitter.emit("pop rax")
            self.emitter.emit("imul rax, 8 ; calc offset into argv")
            self.emitter.emit("lea rbx, [rbp + rax + 8] ; +8 to skip argc")
            self.emitter.emit("mov rdi, [rbx]")

            self.emitter.emit(
                "push rdi ; save rdi to stack because _builtin_c_strlen messes with rdi ptr"
            )
            self.emitter.emit("call __builtin_c_strlen")
            self.emitter.emit("mov rsi, rax ; move length to rsi")
            self.emitter.emit("pop rdi")
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
            self.gen_node_expr_intlit(expr.var.token)
        elif isinstance(expr.var, NodeExprIdent):
            self.gen_node_expr_ident(expr.var.ident)
        elif isinstance(expr.var, NodeExprBinary):
            binary = expr.var
            self.gen_expr(expr.var.lhs)
            self.gen_expr(expr.var.rhs)
            self.emitter.emit("pop rbx; pop rhs")
            self.emitter.emit("pop rax; pop lhs")
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
                self.emitter.emit("cqo ; fill rdx to fit negative or positive number")
                self.emitter.emit("imul rbx")
                self.emitter.emit("push rax; push result")
            elif binary.operator.ttype == TokenType.Slash:
                self.emitter.emit("; division")
                self.emitter.emit("cqo ; fill rdx to fit negative or positive number")
                self.emitter.emit("idiv rbx")
                self.emitter.emit("push rax; push result")
            elif binary.operator.ttype == TokenType.Percent:
                self.emitter.emit("; modulo")
                self.emitter.emit("cqo ; fill rdx to fit negative or positive number")
                self.emitter.emit("idiv rbx")
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

    # NOTE: Should this be Token?
    def gen_node_expr_intlit(self, intlit: Token) -> None:
        # NOTE: What to do when value already exists?
        self.emitter.emit(f"mov rax, {intlit.value}; pushing {intlit.value}")
        self.emitter.emit("push rax")

    # NOTE: Should this be Token?
    def gen_node_expr_ident(self, ident: Token) -> None:
        varinfo = self.symbol_table.lookup(ident.value)
        if varinfo is None:
            raise CodeGenError(
                f"ERROR: {ident.position}: identifier `{ident.value}` was not defined"
            )
        self.emitter.emit(
            f"push qword [rbp{varinfo.offset:+d}] ; push value from variable {ident.value}"
        )

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
