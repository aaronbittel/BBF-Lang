from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class VarType(Enum):
    Int = 8
    String = 16


@dataclass
class VarInfo:
    offset: int
    ttype: VarType


class SymbolTable:
    def __init__(self, parent: SymbolTable | None = None, next_offset: int = -8):
        self.offsets: dict[str, VarInfo] = {}
        self.next_offset = next_offset
        self.parent = parent

    def define(self, name: str, ttype: VarType) -> int:
        offset = self.next_offset
        self.offsets[name] = VarInfo(offset=offset, ttype=ttype)
        self.next_offset -= ttype.value
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
