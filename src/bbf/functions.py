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

    @classmethod
    def from_node(cls, fndef: FnDef) -> "FnInfo":
        name = fndef.name.value
        args = [
            FnArg(param.name.value, VarType.from_token(param.ttype))
            for param in fndef.params
        ]
        return cls(name, args, fndef.ret_vartype)


# Built-in functions
BUILTIN_FNS = {
    "exit": FnInfo("exit", [FnArg("x", IntType)], VoidType),
    "atoi": FnInfo("atoi", [FnArg("x", StringType)], IntType),
    "itoa": FnInfo("itoa", [FnArg("x", IntType)], StringType),
    "btoa": FnInfo("btoa", [FnArg("x", BoolType)], StringType),
    "stdout": FnInfo("stdout", [FnArg("x", StringType)], VoidType),
    "stderr": FnInfo("stderr", [FnArg("x", StringType)], VoidType),
}


class FunctionTable:
    def __init__(self):
        self.fns: dict[str, FnInfo] = dict(BUILTIN_FNS)

    def define(self, fn: FnInfo) -> None:
        if fn.name in self.fns:
            raise ValueError(f"Function `{fn.name}` already defined")
        self.fns[fn.name] = fn

    def lookup(self, name: str) -> FnInfo | None:
        return self.fns.get(name)
