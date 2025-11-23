import argparse
from enum import StrEnum, auto
from pathlib import Path
from typing import Self

from bbf.asm_codegen import AsmCodeGen
from bbf.emitter import Emitter
from bbf.lexer import Lexer, Token
from bbf.nodes.program import ProgTopLevelStmt
from bbf.parser import Parser
from bbf.source import Source
from bbf.utils import run_cmd


class Step(StrEnum):
    Lexer = auto()
    Parser = auto()
    TypeCheck = auto()
    Output = auto()
    All = auto()

    @classmethod
    def from_cli(cls, value: str) -> Self:
        for member in cls:
            if member.name.lower() == value.lower():
                return member
        raise argparse.ArgumentTypeError(f"Invalid step: {value}")

    @property
    def ext(self) -> str:
        match self:
            case Step.Lexer:
                return "tok"
            case Step.Parser:
                return "ast"
            case Step.TypeCheck:
                return "tc"
            case Step.Output:
                return "out"
            case unknown:
                raise ValueError(f"Step {unknown} has no associated extension.")

    def __str__(self) -> str:
        return self.name.lower()


def tokenize(path: Path) -> list[Token]:
    src = path.read_text()
    lexer = Lexer(Source(src, path))
    return lexer.tokenize()


def parse(tokens: list[Token]) -> ProgTopLevelStmt:
    parser = Parser(tokens)
    return parser.parse_prog()


def generate_exe(
    prog: ProgTopLevelStmt, exe_path: Path, *, verbose: bool = False
) -> None:
    main_emitter = Emitter()
    nasm_macros_emitter = Emitter()
    asm_codegen = AsmCodeGen(main_emitter, nasm_macros_emitter)
    asm_codegen.generate_prog(prog)

    basedir = Path(exe_path.parent)
    macros = basedir / "macros.asm"
    asm = exe_path.with_suffix(".asm")
    obj = exe_path.with_suffix(".o")

    with macros.open(mode="w") as macro_out:
        nasm_macros_emitter.write_to(macro_out)

    with asm.open(mode="w") as asm_out:
        main_emitter.write_to(asm_out)

    nasm_cmd = [
        "nasm",
        "-f",
        "elf64",
        "-I",
        str(basedir),
        "-g",
        "-F",
        "dwarf",
        "-o",
        str(obj),
        str(asm),
    ]
    ld_cmd = ["ld", "-o", str(exe_path), str(obj)]

    nasm_res = run_cmd(args=nasm_cmd, echo=verbose)
    if nasm_res.returncode != 0:
        raise RuntimeError(f"nasm failed: {nasm_res.stderr.decode()}")

    ld_res = run_cmd(args=ld_cmd, echo=verbose)
    if ld_res.returncode != 0:
        raise RuntimeError(f"ld failed: {ld_res.stderr.decode()}")
