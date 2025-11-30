from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypeGuard

from bbf.lexer import Token, TokenType


@dataclass(frozen=True)
class VarType(ABC):
    copy_by_value: bool

    @property
    @abstractmethod
    def name(self) -> str: ...
    @property
    @abstractmethod
    def stack_size(self) -> int: ...

    @property
    def fn_param_size(self) -> int:
        if self.copy_by_value:
            return self.stack_size
        return 8

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


@dataclass(frozen=True)
class StringType_(VarType):
    copy_by_value: bool = True

    @property
    def name(self) -> str:
        return "String"

    @property
    def stack_size(self) -> int:
        return 16


IntType = PrimitiveType(t_name="Int", t_size=8, copy_by_value=True)
BoolType = PrimitiveType(t_name="Bool", t_size=8, copy_by_value=True)
VoidType = PrimitiveType(t_name="Void", t_size=0, copy_by_value=True)
StringType = StringType_(copy_by_value=True)


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


@dataclass
class VarInfo:
    name: str
    vartype: VarType
    offset: int
    is_ptr: bool = False


class SymbolTable:
    def __init__(self, parent: SymbolTable | None = None, next_offset: int = -8):
        self.offsets: dict[str, VarInfo] = {}
        self.next_offset = next_offset
        self.parent = parent
        self.reserved_space = 0

    def define_on_stack(self, name: str, vartype: VarType) -> int:
        offset = self.next_offset
        self.offsets[name] = VarInfo(name, vartype, offset)
        self.next_offset -= vartype.stack_size
        self.reserved_space += vartype.stack_size
        return offset

    def define_in_fn(self, name: str, vartype: VarType) -> int:
        offset = self.next_offset
        self.offsets[name] = VarInfo(name, vartype, offset)
        self.next_offset -= vartype.fn_param_size
        self.reserved_space += vartype.fn_param_size
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


def is_slice(vartype: VarType) -> TypeGuard[SliceType]:
    return isinstance(vartype, SliceType)


def is_array(vartype: VarType) -> TypeGuard[ArrayType]:
    return isinstance(vartype, ArrayType)


def is_string(vartype: VarType) -> TypeGuard[StringType_]:
    return isinstance(vartype, StringType_)


def is_primitive(vartype: VarType) -> TypeGuard[PrimitiveType]:
    return isinstance(vartype, PrimitiveType)
