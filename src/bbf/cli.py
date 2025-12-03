import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Self

from bbf import __version__
from bbf.config import BIN_DIR, GLOBAL_BUFFER_CAPACITY
from bbf.runner import Step


@dataclass(frozen=True)
class TypedNamespace:
    filepath: Path
    step: Step = Step.All
    run: list[str] = field(default_factory=list)
    quiet: bool = True
    output: Path = BIN_DIR
    verbose: bool = False
    buffer_size: int = GLOBAL_BUFFER_CAPACITY

    @classmethod
    def from_namespace(cls, args: argparse.Namespace) -> Self:
        return cls(
            args.filepath,
            args.step,
            args.run,
            args.quiet,
            args.output,
            args.verbose,
            args.buffer_size,
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
        "--buffer-size",
        "-b",
        metavar="SIZE",
        type=parse_size,
        default=GLOBAL_BUFFER_CAPACITY,
        help=(
            "Size of the global slice allocation buffer. "
            "Accepts plain bytes or human-readable units like 512K, 2M, 1MiB. "
            "Default: 1MiB."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show the program version and exit",
    )
    return TypedNamespace.from_namespace(parser.parse_args())


def parse_size(s: str) -> int:
    """Parse human-readable sizes like: 1024, 512K, 2M, 1MiB, 4GB Returns the size in bytes."""
    s = s.strip().lower()

    if s.isdigit():
        return int(s)

    units = {
        "k": 1024,
        "kb": 1024,
        "kib": 1024,
        "m": 1024**2,
        "mb": 1024**2,
        "mib": 1024**2,
        "g": 1024**3,
        "gb": 1024**3,
        "gib": 1024**3,
    }

    for suffix, scale in units.items():
        if s.endswith(suffix):
            num = s[: -len(suffix)].strip()
            if not num.replace(".", "", 1).isdigit():
                raise argparse.ArgumentTypeError(f"Invalid size: {s}")
            return int(float(num) * scale)

    raise argparse.ArgumentTypeError(f"Invalid size format: {s}")
