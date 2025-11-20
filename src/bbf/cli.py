import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Self

from bbf import __version__
from bbf.runner import Step

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
    version: bool = False

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


def parse_cli_args() -> TypedNamespace:
    parser = argparse.ArgumentParser(
        prog="bbf",
        description="BBF Compiler: Compile and run BBF source files.",
        add_help=False,
        epilog=(
            "Example usage:\n"
            "  uv run bbf test01.bbf --step output --run arg1 arg2 --verbose\n\n"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("filepath", type=Path, help="Path to input .bbf file")
    parser.add_argument(
        "--step",
        "-s",
        default=Step.All,
        choices=list(Step),
        type=Step.from_cli,
        help=(
            f"Stop compilation at the specified step. The compiler will execute up to this step, "
            f"print its output, and exit with code 0 (default: {Step.All})."
        ),
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
    parser.add_argument(
        "--no-type-check",
        "-ntc",
        action="store_false",
        dest="typecheck",
        help="Disable type checking during compilation.",
    )
    parser.add_argument(
        "--output",
        "-o",
        nargs="?",
        default=BIN_DIR,
        type=Path,
        help="Path to write the compiled executable. "
        "If not provided, defaults to ./bin/<input_filename>.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output: prints commands as they are executed.",
    )
    parser.add_argument(
        "-h",
        "--help",
        action="help",
        help="Show this help message and exit",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show the program version and exit",
    )
    return TypedNamespace.from_namespace(parser.parse_args())
