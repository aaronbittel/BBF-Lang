import subprocess
import sys
from pathlib import Path
from typing import Any, Generator

from bbf.asm_codegen import AsmCodeGen
from bbf.emitter import Emitter
from bbf.lexer import Lexer
from bbf.parser import Parser
from bbf.source import Source


def runner_gen(filepath: Path) -> Generator[tuple[str, Any], None, None]:
    with filepath.open(mode="r") as out:
        src = out.read()

    source = Source(text=src, filepath=filepath)

    lexer = Lexer(source)
    tokens = lexer.tokenize()
    yield "lexer", tokens

    parser = Parser(tokens)
    prog = parser.parse_prog()
    yield "parser", prog

    emitter = Emitter()
    asm_codegen = AsmCodeGen(emitter)
    asm_codegen.generate_prog(prog)
    output_asm = Path(f"./bin/{filepath.stem}.asm")
    with output_asm.open(mode="w") as out:
        emitter.write_to(out)

    output_dir = output_asm.parent
    out_filename = output_asm.stem
    output_o = output_dir / f"{out_filename}.o"
    output_exec = output_dir / out_filename

    nasm_cmd = f"nasm -f elf64 -g -F dwarf -o {output_o} {output_asm}"
    ld_cmd = f"ld -o {output_exec} {output_o}"

    nasm_res = subprocess.run(args=nasm_cmd.split())
    if nasm_res.returncode != 0:
        sys.exit(1)

    ld_res = subprocess.run(args=ld_cmd.split())
    if ld_res.returncode != 0:
        sys.exit(1)

    yield "run", output_exec
