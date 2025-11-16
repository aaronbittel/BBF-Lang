import argparse
import subprocess
import sys
from pathlib import Path

from bbf.ast_printer import ASTPrinter
from bbf.lexer import dump_tokens
from bbf.runner import runner_gen
from bbf.type_checker import TypeChecker
from bbf.utils import green

BIN_DIR = Path("./bin")
BIN_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    argparser = argparse.ArgumentParser(description="Run BBF compiler")
    argparser.add_argument("input_path", type=Path, help="Path to input .bbf file")
    argparser.add_argument(
        "--step",
        default="gen",
        choices=["lexer", "parser", "typecheck", "gen"],
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
    stage: str = args.step
    run_argv: list[str] | None = args.run
    quiet: bool = args.quiet
    type_check: bool = args.type_check

    runner = runner_gen(input_path)

    step, tokens = next(runner)
    if stage == step:
        dump_tokens(tokens)
        sys.exit(0)

    step, prog = next(runner)
    if stage == step:
        prog.accept(ASTPrinter())
        sys.exit(0)

    if type_check:
        prog.accept(TypeChecker())
        if not quiet:
            print(green(f"[INFO] Successfully type checked `{input_path}`"))
        if stage == "typecheck":
            sys.exit(0)

    step, output_exec = next(runner)
    if not quiet:
        print(green(f"[INFO] Successfully compiled program to `{output_exec}`"))

    if run_argv is not None:
        run_cmd = f"{output_exec} {' '.join(run_argv)}"
        run_res = subprocess.run(args=run_cmd.split())
        exit_code = run_res.returncode
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
