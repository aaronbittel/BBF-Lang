from __future__ import annotations

from copy import deepcopy
from functools import partial
from typing import NamedTuple

from bbf.nodes.toplevel import FnDef
from bbf.varinfo import BoolType, IntType, StringType, VarType, VoidType


class FnArg(NamedTuple):
    name: str
    vartype: VarType


class FnInfo(NamedTuple):
    name: str
    args: list[FnArg]
    return_type: VarType
    prefix: str = ""

    @classmethod
    def from_node(cls, fndef: FnDef) -> FnInfo:
        name = fndef.name.value
        args = [FnArg(param.name.value, param.vartype) for param in fndef.params]
        return cls(name, args, fndef.ret_vartype)

    @property
    def callname(self) -> str:
        return f"{self.prefix}{self.name}"


syscall = partial(FnInfo, prefix="__sys_")
builtin = partial(FnInfo, prefix="__builtin_")


# Built-in functions
BUILTIN_FNS = {
    "exit": syscall("exit", [FnArg("x", IntType)], VoidType),
    "stdout": syscall("stdout", [FnArg("x", StringType)], VoidType),
    "stderr": syscall("stderr", [FnArg("x", StringType)], VoidType),
    "atoi": builtin("atoi", [FnArg("x", StringType)], IntType),
    "itoa": builtin("itoa", [FnArg("x", IntType)], StringType),
    "btoa": builtin("btoa", [FnArg("x", BoolType)], StringType),
    "read_entire_file": builtin(
        "read_entire_file", [FnArg("filename", StringType)], StringType
    ),
}


class FunctionTable:
    def __init__(self):
        self.fns: dict[str, FnInfo] = deepcopy(BUILTIN_FNS)

    def define(self, fn: FnInfo) -> None:
        if fn.name in self.fns:
            raise ValueError(f"Function `{fn.name}` already defined")
        self.fns[fn.name] = fn

    def lookup(self, name: str) -> FnInfo | None:
        return self.fns.get(name)
