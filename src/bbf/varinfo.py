from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from bbf.lexer import Token, TokenType


class VarType(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def stack_size(self) -> int: ...
    @property
    def is_slice(self) -> bool: ...

    @staticmethod
    def from_token(token: Token) -> VarType:
        if token.ttype == TokenType.Int:
            return IntType
        elif token.ttype == TokenType.String:
            return StringType
        elif token.ttype == TokenType.Bool:
            return BoolType
        elif token.ttype == TokenType.Void:
            return VoidType
        else:
            raise ValueError(f"Cannot convert token {token.value} to VarType")


@dataclass(frozen=True)
class PrimitiveType(VarType):
    t_name: str
    t_size: int

    @property
    def name(self) -> str:
        return self.t_name

    @property
    def stack_size(self) -> int:
        return self.t_size

    @property
    def is_slice(self) -> bool:
        return False


@dataclass(frozen=True)
class StringType_(VarType):
    @property
    def name(self) -> str:
        return "String"

    @property
    def stack_size(self) -> int:
        return 16

    @property
    def is_slice(self) -> bool:
        return True


IntType = PrimitiveType("Int", 8)
BoolType = PrimitiveType("Bool", 8)
VoidType = PrimitiveType("Void", 0)
StringType = StringType_()


@dataclass(frozen=True)
class ArrayType(VarType):
    vartype: VarType
    length: int

    @property
    def name(self) -> str:
        return f"{self.vartype.name}[{self.length}]"

    @property
    def stack_size(self) -> int:
        return 16

    @property
    def is_slice(self) -> bool:
        return True

    @property
    def total_size(self) -> int:
        return self.vartype.stack_size * self.length


@dataclass(frozen=True)
class SliceType(VarType):
    vartype: VarType

    @property
    def name(self) -> str:
        return f"[{self.vartype.name}]"

    @property
    def stack_size(self) -> int:
        return 24

    @property
    def is_slice(self) -> bool:
        return True


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
        self.next_offset -= vartype.stack_size
        self.reserved_space += vartype.stack_size
        return offset

    def lookup(self, name: str) -> VarInfo | None:
        if name in self.offsets:
            return self.offsets[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def reserve(self, size: int) -> None:
        self.next_offset -= size
        self.reserved_space += size
