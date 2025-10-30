from typing import Callable

import pytest

from bbf.lexer import Lexer, LexerError, Token, TokenType
from tests.bbf.helpers import (
    TEST_PATH,
    assign,
    closep,
    div,
    eof,
    fn_exit,
    ident,
    integer,
    minus,
    mult,
    openp,
    p,
    plus,
    string,
)


@pytest.fixture
def make_lexer() -> Callable[[str], Lexer]:
    def _make_lexer(src: str):
        return Lexer(path=TEST_PATH, src=src)

    return _make_lexer


@pytest.mark.parametrize(
    "src, expected",
    [
        ("", eof()),
        ("(", openp()),
        (")", closep()),
        ("15352", integer(value=15352)),
        ("+", plus()),
        ("-", minus()),
        ("*", mult()),
        ("/", div()),
        ('"Hello, World!"', string(value="Hello, World!")),
        ("x_5", ident(value="x_5")),
        ("# comment", eof()),
    ],
)
def test_single_token(make_lexer: Callable[[str], Lexer], src: str, expected: Token):
    lexer = make_lexer(src)
    token = lexer.next_token()

    assert token == expected


@pytest.mark.parametrize(
    "src, expected_tokens",
    [
        (
            "exit(52)",
            [
                fn_exit(column=1),
                openp(column=5),
                integer(value=52, column=6),
                closep(column=8),
            ],
        ),
        (
            "x = 5\nexit(x)",
            [
                ident(value="x", column=1),
                assign(column=3),
                integer(value=5, column=5),
                fn_exit(line=2, column=1),
                openp(line=2, column=5),
                ident(value="x", line=2, column=6),
                closep(line=2, column=7),
            ],
        ),
        (
            "x = 54 - 12 + (*) / ",
            [
                ident(value="x", column=1),
                assign(column=3),
                integer(value=54, column=5),
                minus(column=8),
                integer(value=12, column=10),
                plus(column=13),
                openp(column=15),
                mult(column=16),
                closep(column=17),
                div(column=19),
            ],
        ),
        (
            's = "Hello, World!" x_5\n\nsome tokens\n',
            [
                ident(value="s"),
                assign(column=3),
                string(value="Hello, World!", column=5),
                ident(value="x_5", column=21),
                ident(value="some", line=3, column=1),
                ident(value="tokens", line=3, column=6),
            ],
        ),
        (
            "# comment\nzzz = - 23 # inline",
            [
                ident(value="zzz", line=2),
                assign(line=2, column=5),
                minus(line=2, column=7),
                integer(value=23, line=2, column=9),
            ],
        ),
        ('"String with # !"', [string("String with # !")]),
    ],
)
def test_multi_token(
    make_lexer: Callable[[str], Lexer], src: str, expected_tokens: list[Token]
):
    lexer = make_lexer(src)
    index = 0
    while (token := lexer.next_token()) and token.ttype != TokenType.EOF:
        expected = expected_tokens[index]
        assert token == expected
        index += 1

    assert index == len(expected_tokens), (
        f"expected all tokens to be consumed, but missed the following: {expected_tokens[index:]}"
    )


@pytest.mark.parametrize(
    "src, error",
    [
        ("523sfa", LexerError(msg="invalid integer literal", position=p(column=4))),
        ("@", LexerError(msg="invalid character @", position=p())),
        ('"H', LexerError(msg="unterminated string literal", position=p())),
    ],
)
def test_lexing_error(make_lexer: Callable[[str], Lexer], src: str, error: LexerError):
    lexer = make_lexer(src)
    with pytest.raises(LexerError) as excinfo:
        lexer.next_token()
    assert str(excinfo.value) == str(error)
