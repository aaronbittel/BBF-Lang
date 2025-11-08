from dataclasses import dataclass
from enum import StrEnum, auto


class VarType(StrEnum):
    Int = auto()
    String = auto()


@dataclass
class VarInfo:
    offset: int
    ttype: VarType


class SymbolTable:
    def __init__(self):
        self.offsets: dict[str, VarInfo] = {}
        self.next_offset = 8

    def define(self, name: str, ttype: VarType) -> int:
        offset = self.next_offset
        self.offsets[name] = VarInfo(offset=offset, ttype=ttype)
        self.next_offset += 8
        return offset

    def lookup(self, name: str) -> VarInfo | None:
        return self.offsets.get(name)
