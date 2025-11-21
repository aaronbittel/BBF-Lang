from dataclasses import dataclass

from bbf.vartype import VarType


@dataclass
class VarInfo:
    name: str
    vartype: VarType
    offset: int


class SymbolTable:
    def __init__(self, parent: "SymbolTable | None" = None, next_offset: int = -8):
        self.offsets: dict[str, VarInfo] = {}
        self.next_offset = next_offset
        self.parent = parent
        self.reserved_space = 0

    def define(self, name: str, vartype: VarType) -> int:
        offset = self.next_offset
        self.offsets[name] = VarInfo(name, vartype, offset)
        self.next_offset -= vartype.value
        self.reserved_space += vartype.value
        return offset

    def lookup(self, name: str) -> VarInfo | None:
        if name in self.offsets:
            return self.offsets[name]
        if self.parent:
            return self.parent.lookup(name)
        return None
