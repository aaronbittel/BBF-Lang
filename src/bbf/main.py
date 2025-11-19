import argparse
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Self

from bbf.ast_printer import ASTPrinter
from bbf.lexer import dump_tokens
from bbf.runner import Step, generate_exe, parse, tokenize
from bbf.type_checker import TypeChecker
from bbf.utils import blue, green

BIN_DIR = Path("./bin")
BIN_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class TypedNamespace:
    filepath: Path
    step: Step = Step.All
    run: list[str] = field(default_factory=list)
    quiet: bool = True
    typecheck: bool = True
    output: Path = BIN_DIR
    verbose: bool = False

    @classmethod
    def from_namespace(cls, args: argparse.Namespace) -> Self:
        return cls(
            args.filepath,
            args.step,
            args.run,
            args.quiet,
            args.typecheck,
            args.output,
            args.verbose,
        )


def main() -> None:
    argparser = argparse.ArgumentParser(description="Run BBF compiler")
    argparser.add_argument("filepath", type=Path, help="Path to input .bbf file")
    argparser.add_argument(
        "--step",
        "-s",
        default=Step.All,
        choices=list(Step),
        type=Step.from_cli,
        help=f"Compilation step (default: {Step.All})",
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
        help="args.quiet mode. Don't print any info about compilation phases.",
    )
    argparser.add_argument(
        "--no-type-check",
        "-ntc",
        action="store_false",
        dest="typecheck",
        help="Disable type checking during compilation.",
    )
    argparser.add_argument(
        "--output",
        "-o",
        nargs="?",
        default=BIN_DIR,
        type=Path,
        help="Directory to write the compiled executable into (default: ./bin).",
    )
    argparser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output.",
    )
    args = TypedNamespace.from_namespace(argparser.parse_args())

    tokens = tokenize(args.filepath)
    if args.step == Step.Lexer:
        dump_tokens(tokens)
        sys.exit(0)

    prog = parse(tokens)
    if args.step == Step.Parser:
        prog.accept(ASTPrinter())
        sys.exit(0)

    if args.typecheck or args.step == Step.TypeCheck:
        prog.accept(TypeChecker())
        if not args.quiet:
            print(green(f"[INFO] Successfully type checked `{args.filepath}`"))
        if args.step == Step.TypeCheck:
            sys.exit(0)

    exe_path = args.output / args.filepath.stem if args.output.is_dir() else args.output
    generate_exe(prog, exe_path=exe_path, verbose=args.verbose)
    if not args.quiet:
        print(green(f"[INFO] Successfully compiled program to `{args.output}`"))

    if args.run is not None:
        run_cmd = [str(exe_path), *args.run]
        if args.verbose:
            print(blue("[INFO]"), " ".join(run_cmd))
        run_res = subprocess.run(args=run_cmd)
        sys.exit(run_res.returncode)


if __name__ == "__main__":
    main()
