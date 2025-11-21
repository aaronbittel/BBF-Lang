from typing import NamedTuple

from bbf.nodes.toplevel import FnDef
from bbf.varinfo import VarType


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
        return_type = VarType.from_token(fndef.return_ttype)
        return cls(name, args, return_type)


# Built-in functions
BUILTIN_FNS = {
    "exit": FnInfo("exit", [FnArg("x", VarType.Int)], VarType.Void),
    "atoi": FnInfo("atoi", [FnArg("x", VarType.String)], VarType.Int),
    "itoa": FnInfo("itoa", [FnArg("x", VarType.Int)], VarType.String),
    "btoa": FnInfo("btoa", [FnArg("x", VarType.Bool)], VarType.String),
    "stdout": FnInfo("stdout", [FnArg("x", VarType.String)], VarType.Void),
    "stderr": FnInfo("stderr", [FnArg("x", VarType.String)], VarType.Void),
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
