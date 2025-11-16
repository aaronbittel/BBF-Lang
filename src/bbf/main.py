import argparse
import subprocess
import sys
from pathlib import Path

from bbf.asm_codegen import AsmCodeGen
from bbf.ast_printer import ASTPrinter
from bbf.emitter import Emitter
from bbf.lexer import Lexer, dump_tokens
from bbf.parser import Parser
from bbf.source import Source
from bbf.type_checker import TypeChecker
from bbf.utils import GREEN, RED, RESET, eprint, green, red

BIN_DIR = Path("./bin")
BIN_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    argparser = argparse.ArgumentParser(description="Run BBF compiler")
    argparser.add_argument("input_path", type=Path, help="Path to input .bbf file")
    argparser.add_argument(
        "--step",
        default="gen",
        choices=["lexer", "parser", "typechecker", "gen"],
        help="Compilation step (default: gen)",
    )
    argparser.add_argument(
        "--run",
        "-r",
        nargs="*",
        metavar="ARGS",
        help="Run the program after successful compilation (optionally with ARGS as argv)",
    )
    argparser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Quiet mode. Don't print any info about compilation phases.",
    )
    argparser.add_argument(
        "--no-type-check",
        "-ntc",
        action="store_false",
        dest="type_check",
        help="Disable type checking during compilation.",
    )
    args = argparser.parse_args()

    input_path: Path = args.input_path
    step: str = args.step
    run_argv: list[str] | None = args.run
    quiet: bool = args.quiet
    type_check: bool = args.type_check

    with args.input_path.open(mode="r") as out:
        src = out.read()

    if not quiet:
        print(f"[INFO] Read input file: {input_path}")
        print(src)
        print("=====================")

    source = Source(text=src, filepath=input_path)

    lexer = Lexer(source)
    tokens = lexer.tokenize()

    if not quiet:
        print("[INFO] Parsed into Tokens:")
        dump_tokens(tokens)
        print("=====================")

    if step == "lexer":
        sys.exit(0)

    parser = Parser(tokens)
    prog = parser.parse_program()
    if not quiet:
        print("[INFO] Parsed into AST:")
        ast_printer = ASTPrinter()
        for toplevel in prog.stmts:
            toplevel.accept(ast_printer)
        print("=====================")

    if step == "parser":
        sys.exit(0)

    if type_check:
        if not quiet:
            print("[INFO] Type Checking AST:")
        type_checker = TypeChecker()
        for toplevel in prog.stmts:
            toplevel.accept(type_checker)
        if not quiet:
            print(green("[INFO] Successfully type checked!"))
            print("=====================")

    if step == "typechecker":
        sys.exit(0)

    emitter = Emitter()
    asm_codegen = AsmCodeGen(emitter)
    asm_codegen.generate_prog(prog)
    output_asm = Path(f"./bin/{input_path.stem}.asm")
    if not quiet:
        print(f"[INFO] Writing assembly output to {output_asm}")
    with output_asm.open(mode="w") as out:
        emitter.write_to(out)

    output_dir = output_asm.parent
    out_filename = output_asm.stem
    output_o = output_dir / f"{out_filename}.o"
    output_path = output_dir / out_filename

    nasm_cmd = f"nasm -f elf64 -g -F dwarf -o {output_o} {output_asm}"
    ld_cmd = f"ld -o {output_path} {output_o}"

    nasm_res = subprocess.run(args=nasm_cmd.split())
    if not quiet:
        print(f"[INFO] {nasm_cmd}")
    if nasm_res.returncode != 0:
        eprint(red("[ERROR] nasm Failed"))
        sys.exit(1)

    ld_res = subprocess.run(args=ld_cmd.split())
    if not quiet:
        print(f"[INFO] {ld_cmd}")
    if ld_res.returncode != 0:
        eprint(red("[ERROR] ld Failed"))
        sys.exit(1)

    if not quiet:
        print(green("[INFO] Successfully compiled!"))

    if run_argv is None:
        sys.exit(0)

    if not quiet:
        print()

    run_cmd = f"{output_path} {' '.join(run_argv)}"
    run_res = subprocess.run(args=run_cmd.split())
    if not quiet:
        print(f"[INFO] {run_cmd}")
    exit_code = run_res.returncode
    prefix = f"{GREEN}[INFO]" if exit_code == 0 else f"{RED}[ERROR]"
    if not quiet:
        print(f"{prefix} {output_path} exited with exitcode {exit_code}{RESET}")
    sys.exit(run_res.returncode)


if __name__ == "__main__":
    main()
