import pytest

from bbf.lexer import Token
from bbf.parser import NodeProgram, Parser
from tests.bbf.helpers import (
    assign,
    assign_stmt,
    closep,
    eof,
    exit_stmt,
    fn_exit,
    ident,
    ident_expr,
    int_lit,
    integer,
    openp,
)


# NOTE: currently the position is ignored in this tests
@pytest.mark.parametrize(
    "tokens, expected_ast",
    [
        (
            [ident("x"), assign(), integer(5), eof()],
            NodeProgram([assign_stmt("x", int_lit(5))]),
        ),
        (
            [fn_exit(), openp(), integer(42), closep(), eof()],
            NodeProgram([exit_stmt(int_lit(42))]),
        ),
        (
            [ident("x"), assign(), ident("y"), eof()],
            NodeProgram([assign_stmt("x", ident_expr("y"))]),
        ),
    ],
)
def test_single_statements(tokens: list[Token], expected_ast: NodeProgram):
    parser = Parser(tokens)
    ast = parser.parse_program()
    assert ast == expected_ast


# NOTE: currently the position is ignored in this tests
# fmt: off
@pytest.mark.parametrize(
    "tokens, expected_ast",
    [
        (
            [
                ident("x"), assign(), integer(5), # x = 5
                fn_exit(), openp(), integer(42), closep(), # exit(42)
                ident("x"), assign(), ident("y"), # x = y
                eof(),
            ],
            NodeProgram([
                assign_stmt("x", int_lit(5)),
                exit_stmt(int_lit(42)),
                assign_stmt("x", ident_expr("y"))
            ])
        ),
    ],
)
# fmt: on
def test_multiple_statments(tokens: list[Token], expected_ast: NodeProgram):
    pass
