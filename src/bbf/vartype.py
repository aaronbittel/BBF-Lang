from enum import Enum

from bbf.lexer import Token, TokenType


class VarType(Enum):
    Int = 8
    String = 16
    Void = 0
    Bool = 8

    @classmethod
    def from_token(cls, token: Token) -> "VarType":
        if token.ttype == TokenType.Int:
            return cls.Int
        if token.ttype == TokenType.String:
            return cls.String
        if token.ttype == TokenType.Void:
            return cls.Void
        if token.ttype == TokenType.Bool:
            return cls.Bool
        assert False, f"unreachable: can't match token {token} to `VarType`"

    def __str__(self) -> str:
        return self.name
