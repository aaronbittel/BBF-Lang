import argparse
import subprocess
import sys
from pathlib import Path

from bbf.generation import CodeGenerator
from bbf.lexer import Lexer, dump_tokens
from bbf.parser import Parser
from bbf.utils import GREEN, RED, RESET, eprint, green, red

# TODO: Use snapshot testing

BIN_DIR = Path("./bin")
BIN_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run BBF compiler")
    parser.add_argument("input_path", type=Path, help="Path to input .bbf file")
    parser.add_argument(
        "--step",
        default="gen",
        choices=["lexer", "parser", "gen"],
        help="Compilation step (default: gen)",
    )
    parser.add_argument(
        "--run",
        "-r",
        nargs="*",
        metavar="ARGS",
        help="Run the program after successful compilation (optionally with ARGS as argv)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Quiet mode. Don't print any info about compilation phases.",
    )
    args = parser.parse_args()

    input_path: Path = args.input_path
    step: str = args.step
    run_argv: list[str] = args.run
    quiet: bool = args.quiet

    with args.input_path.open(mode="r") as f:
        src = f.read()

    if not quiet:
        print(f"[INFO] Read input file: {input_path}")
        print(src)
        print("=====================")

    lexer = Lexer(path=input_path, src=src)
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
        print("[INFO] Parsed into:")
        print(prog)
        print("=====================")

    if step == "parser":
        sys.exit(0)

    output_asm = Path(f"./bin/{input_path.stem}.asm")
    code_gen = CodeGenerator(prog=prog)
    if not quiet:
        print(f"[INFO] Writing assembly output to {output_asm}")
    code_gen.gen_prog()
    with output_asm.open(mode="w") as f:
        code_gen.write_to(f)

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
