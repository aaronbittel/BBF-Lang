from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from functools import partial
from typing import Callable, NamedTuple

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


def make_append_method(elem_type: VarType) -> FnInfo:
    return builtin("append", [FnArg("elem", elem_type)], VoidType)


def make_len_method(elem_type: VarType) -> FnInfo:
    return builtin("len", [], IntType)


def make_cap_method(elem_type: VarType) -> FnInfo:
    return builtin("cap", [], IntType)


@dataclass(frozen=True)
class SliceMethod:
    factory: Callable[..., FnInfo]
    field_access: bool = True
    field_offset: int = 0


SLICE_METHODS: dict[str, SliceMethod] = {
    "append": SliceMethod(factory=make_append_method, field_access=False),
    "len": SliceMethod(factory=make_len_method, field_access=True, field_offset=8),
    "cap": SliceMethod(factory=make_cap_method, field_access=True, field_offset=16),
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
