from io import StringIO

from bbf.generation import CodeGenerator
from bbf.parser import NodeProgram
from tests.bbf.helpers import assign_stmt, exit_stmt, int_lit


def test_gen_stmt_exit():
    stmt = exit_stmt(int_lit(12))
    prog = NodeProgram([stmt])
    code_gen = CodeGenerator(prog)
    code_gen.gen_stmt_exit(stmt)
    expected = "\n".join(
        ["; exit(12)", "mov rax, 12", "mov rdi, rax", "call __builtin_exit"]
    )
    generated = StringIO()
    code_gen.emitter.write_to(generated)
    generated_str = "\n".join(
        map(lambda s: s.strip(), generated.getvalue().split("\n"))
    )
    assert generated_str == expected


def test_gen_stmt_assign():
    stmt = assign_stmt(name="variable", expr=int_lit(12142))
    prog = NodeProgram([stmt])
    code_gen = CodeGenerator(prog)
    code_gen.gen_stmt_decl(stmt)
    expected = "\n".join(["; assign(variable = 12142)", "mov rax, 12142", "push rax"])
    generated = StringIO()
    code_gen.emitter.write_to(generated)
    generated_str = "\n".join(
        map(lambda s: s.strip(), generated.getvalue().split("\n"))
    )
    assert generated_str == expected
