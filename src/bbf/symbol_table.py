from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple, Self

from bbf.lexer import Token, TokenType
from bbf.nodes.toplevel import FnDef


class VarType(Enum):
    Int = 8
    String = 16
    Void = 0

    @classmethod
    def from_token(cls, token: Token) -> VarType:
        if token.ttype == TokenType.Int:
            return cls.Int
        if token.ttype == TokenType.String:
            return cls.String
        if token.ttype == TokenType.Void:
            return cls.Void
        assert False, f"unreachable: can't match token {token} to `VarType`"


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

    def define(self, name: str, ttype: VarType) -> int:
        offset = self.next_offset
        self.offsets[name] = VarInfo(name, ttype, offset)
        self.next_offset -= ttype.value
        self.reserved_space += ttype.value
        return offset

    def lookup(self, name: str) -> VarInfo | None:
        varinfo = self.offsets.get(name)
        # variable defined in this scope
        if varinfo is not None:
            return varinfo
        cur = self.parent
        while cur is not None:
            varinfo = cur.lookup(name)
            if varinfo is not None:
                return varinfo
            cur = cur.parent
        return None


class FnArg(NamedTuple):
    name: str
    vartype: VarType

    def __str__(self) -> str:
        return f"{self.name}: {self.vartype.name}"


class FnInfo(NamedTuple):
    name: str
    args: list[FnArg]
    return_type: VarType

    @classmethod
    def from_node(cls, fndef: FnDef) -> Self:
        name = fndef.name.value
        args = [
            FnArg(param.name.value, VarType.from_token(param.vartype))
            for param in fndef.params
        ]
        return_type = VarType.from_token(fndef.return_type)
        return cls(name, args, return_type)

    def __str__(self) -> str:
        args = map(lambda arg: f"{arg.name}: {arg.vartype.name}", self.args)
        return f"Fn: {self.name} ( {', '.join(args)} ) -> {self.return_type.name}"


# TODO: Implement function overloads e.g. for print
BUILTIN_FNS = {
    "exit": FnInfo(
        name="exit",
        args=[FnArg(name="x", vartype=VarType.Int)],
        return_type=VarType.Void,
    ),
    "atoi": FnInfo(
        name="atoi",
        args=[FnArg(name="x", vartype=VarType.String)],
        return_type=VarType.Int,
    ),
    "itoa": FnInfo(
        name="itoa",
        args=[FnArg(name="x", vartype=VarType.Int)],
        return_type=VarType.String,
    ),
    "stdout": FnInfo(
        name="stdout",
        args=[FnArg(name="x", vartype=VarType.String)],
        return_type=VarType.Void,
    ),
    "stderr": FnInfo(
        name="stderr",
        args=[FnArg(name="x", vartype=VarType.String)],
        return_type=VarType.Void,
    ),
}


class FunctionTable:
    def __init__(self) -> None:
        self.fns = BUILTIN_FNS

    def define(self, fn: FnInfo) -> None:
        assert fn.name not in self.fns, (
            f"Fn `{fn.name}` is already defined as {self.fns[fn.name]}"
        )
        self.fns[fn.name] = fn

    def lookup(self, name: str) -> FnInfo | None:
        return self.fns.get(name)
