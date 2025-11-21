from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from bbf.lexer import Token, TokenType


class VarType(Enum):
    Int = ("Int", 8)
    String = ("String", 16)
    Void = ("Void", 0)
    Bool = ("Bool", 8)

    def __init__(self, name: str, size: int) -> None:
        self._name = name
        self._size = size

    @classmethod
    def from_token(cls, token: Token) -> VarType:
        if token.ttype == TokenType.Int:
            return cls.Int
        if token.ttype == TokenType.String:
            return cls.String
        if token.ttype == TokenType.Void:
            return cls.Void
        if token.ttype == TokenType.Bool:
            return cls.Bool
        assert False, f"unreachable: can't match token {token} to `VarType`"

    @property
    def size(self) -> int:
        return self._size

    def __str__(self) -> str:
        return self._name


@dataclass
class VarInfo:
    name: str
    vartype: VarType
    offset: int


class SymbolTable:
    def __init__(self, parent: SymbolTable | None = None, next_offset: int = -8):
        self.offsets: dict[str, VarInfo] = {}
        self.next_offset = next_offset
        self.parent = parent
        self.reserved_space = 0

    def define(self, name: str, vartype: VarType) -> int:
        offset = self.next_offset
        self.offsets[name] = VarInfo(name, vartype, offset)
        self.next_offset -= vartype.size
        self.reserved_space += vartype.size
        return offset

    def lookup(self, name: str) -> VarInfo | None:
        if name in self.offsets:
            return self.offsets[name]
        if self.parent:
            return self.parent.lookup(name)
        return None
