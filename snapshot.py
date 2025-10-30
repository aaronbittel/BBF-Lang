import argparse
from contextlib import suppress
from dataclasses import dataclass
import sys
from pathlib import Path

from bbf.generation import CodeGenerator
from bbf.lexer import Lexer, Token, TokenType
from bbf.parser import (
    Parser,
)
from bbf.utils import green, red


SNAPSHOTS_DIR = Path("./tests/snapshots/")
EXAMPLES_DIR = Path("./examples/")

parser = argparse.ArgumentParser(
    description="BBF Language Snapshot Tester and Recorder",
    epilog="Use `run` to check snapshots or `record` to update them.",
)

subparsers = parser.add_subparsers(
    dest="command",
    required=True,
    title="subcommands",
    description="Valid subcommands",
)

# -----------------------
# RUN SUBCOMMAND
# -----------------------
run_parser = subparsers.add_parser(
    "run",
    help="Run snapshot tests for one or more BBF files.",
    description=(
        "Run all defined snapshot tests (lexer, parser, generation) "
        f"for a specific BBF file or all files in the ./{EXAMPLES_DIR} directory."
    ),
)

run_parser.add_argument(
    "-s",
    "--step",
    help=(
        "Specify which steps to test. "
        "`lexer` runs lexer snapshot, `parser` runs parser snapshot, "
        "`gen` runs code generation snapshot, `all` runs everything."
    ),
    choices=["lexer", "parser", "gen", "all"],
    default=["all"],
    nargs="+",
    type=str,
)

run_parser.add_argument(
    "filepath",
    nargs="?",
    type=Path,
    help=(
        "Optional path to a single .bbf file. "
        f"If omitted, all .bbf files in ./{EXAMPLES_DIR} are used."
    ),
)

# -----------------------
# RECORD SUBCOMMAND
# -----------------------
record_parser = subparsers.add_parser(
    "record",
    help="Record snapshot files for a given BBF file.",
    description=(
        "Generate or update snapshot files for lexer, parser, and code generation "
        "for a single BBF source file."
    ),
)

record_parser.add_argument(
    "-s",
    "--step",
    help=(
        "Specify which steps to record. "
        "`lexer` records lexer output, `parser` records parser AST, "
        "`gen` records generated code, `all` records everything."
    ),
    choices=["lexer", "parser", "gen", "all"],
    default=["all"],
    nargs="+",
    type=str,
)

record_parser.add_argument(
    "filepath",
    help=f"Path to the BBF file to record snapshots for. Must exist in ./{EXAMPLES_DIR}.",
    type=Path,
)

# -----------------------
# CLEAN SUBCOMMAND
# -----------------------
clean_parser = subparsers.add_parser(
    "clean",
    help="Remove all .actual snapshot files.",
    description=(
        "Delete all '.actual' files in the snapshot directory. "
        "These files are generated when a snapshot test fails "
        "and are safe to remove."
    ),
)


def handle_diff(path: Path, expected_lines: list[str], actual_lines: list[str]) -> None:
    diff_lines = format_diff_lines(expected_lines, actual_lines)
    if diff_lines:
        print()
        for diff in diff_lines:
            print(f"LINE {diff.line}: '{diff.actual}'")
            print(f"LINE {diff.line}: '{diff.expected}'")
        path_actual = path.with_suffix(".actual")
        path_actual.write_text("\n".join(actual_lines))
        print(f"[INFO] Saved actual gen output to {path_actual}")
    else:
        print(green("[SUCCESS]"))


@dataclass
class DiffLine:
    line: int
    expected: str
    actual: str


def format_diff_lines(
    expected_lines: list[str], actual_lines: list[str]
) -> list[DiffLine]:
    """Return a list of colorized diff lines between expected and actual text."""
    diffed_lines: list[DiffLine] = []

    for line_nr, (expected_line, actual_line) in enumerate(
        zip(expected_lines, actual_lines), start=1
    ):
        if expected_line == actual_line:
            continue

        diff_indices: list[int] = [
            i
            for i, (exp_ch, act_ch) in enumerate(zip(expected_line, actual_line))
            if exp_ch != act_ch
        ]

        actual_colored = "".join(
            red(ch) if i in diff_indices else ch for i, ch in enumerate(actual_line)
        )
        expected_colored = "".join(
            green(ch) if i in diff_indices else ch for i, ch in enumerate(expected_line)
        )

        diffed_lines.append(
            DiffLine(line=line_nr, actual=actual_colored, expected=expected_colored)
        )

    return diffed_lines


def lexer_snapshot_path(path: Path) -> Path:
    return (SNAPSHOTS_DIR / path.stem).with_suffix(".tok.snap")


def parser_snapshot_path(name: str) -> Path:
    return (SNAPSHOTS_DIR / path.stem).with_suffix(".ast.snap")


def gen_snapshot_path(name: str) -> Path:
    return (SNAPSHOTS_DIR / path.stem).with_suffix(".gen.snap")


if __name__ == "__main__":
    args = parser.parse_args()

    if args.command == "record":
        path = args.filepath
        assert isinstance(path, Path)
        if path.parent != EXAMPLES_DIR or not path.exists():
            print(red(f"ERROR: file {path} does not exist in {EXAMPLES_DIR}"))
            sys.exit(1)
        src = path.read_text()
        lexer = Lexer(path, src)
        tokens: list[Token] = []
        while token := lexer.next_token():
            tokens.append(token)
            if token.ttype == TokenType.EOF:
                break
        steps: list[str] = args.step
        if "lexer" in steps or "all" in steps:
            lexer_snapshot = lexer_snapshot_path(path)
            lexer_snapshot.write_text("\n".join(repr(token) for token in tokens))
            print(f"[INFO] Recorded `token` output for {path} into {lexer_snapshot}")

        parser = Parser(tokens)
        prog = parser.parse_program()
        if "parser" in steps or "all" in steps:
            parser_snapshot = parser_snapshot_path(path)
            parser_snapshot.write_text("\n".join(str(stmt) for stmt in prog.stmts))
            print(f"[INFO] Recorded `parser` output for {path} into {parser_snapshot}")

        if "gen" in steps or "all" in steps:
            code_gen = CodeGenerator(prog)
            code_gen.gen_prog()
            gen_snapshot = gen_snapshot_path(path)
            with gen_snapshot.open("w", encoding="utf-8") as f:
                code_gen.write_to(f)
            print(f"[INFO] Recorded `gen` output for {path} into {gen_snapshot}")

    elif args.command == "run":
        files_to_run = (
            [args.filepath] if args.filepath else list(EXAMPLES_DIR.glob("*.bbf"))
        )

        missing_snapshots: list[tuple[Path, str]] = []
        for path in files_to_run:
            src = path.read_text()
            lexer = Lexer(path, src)
            tokens: list[Token] = []
            while token := lexer.next_token():
                tokens.append(token)
                if token.ttype == TokenType.EOF:
                    break

            lexer_snapshot = lexer_snapshot_path(path)
            if not lexer_snapshot.exists():
                missing_snapshots.append((path, "lexer"))
            else:
                if "lexer" in args.step or "all" in args.step:
                    print(f"[INFO] Running lexer snapshot for `{path.name}`", end=" ")
                    expected_lines = lexer_snapshot.read_text().splitlines()
                    actual_lines = [repr(token) for token in tokens]
                    handle_diff(lexer_snapshot, expected_lines, actual_lines)

            parser_snapshot = parser_snapshot_path(path)
            if not parser_snapshot.exists():
                missing_snapshots.append((path, "parser"))
            else:
                parser = Parser(tokens)
                prog = parser.parse_program()

                if "parser" in args.step or "all" in args.step:
                    print(f"[INFO] Running parser snapshot for `{path.name}`", end=" ")
                    expected_lines = parser_snapshot.read_text().splitlines()
                    actual_lines = [str(stmt) for stmt in prog.stmts]
                    handle_diff(parser_snapshot, expected_lines, actual_lines)

            gen_snapshot = gen_snapshot_path(path)
            if not gen_snapshot.exists():
                missing_snapshots.append((path, "gen"))
            else:
                if "gen" in args.step or "all" in args.step:
                    print(f"[INFO] Running gen snapshot for `{path.name}`", end=" ")
                    code_gen = CodeGenerator(prog)
                    code_gen.gen_prog()

                    expected_lines = gen_snapshot.read_text().splitlines()
                    actual_lines = code_gen.emitter.lines
                    handle_diff(gen_snapshot, expected_lines, actual_lines)

        for snap, step in missing_snapshots:
            print(
                red(f"[INFO]: `{step}` snapshot for file {snap.name} does not exist.")
            )
    elif args.command == "clean":
        actual_files = list(SNAPSHOTS_DIR.glob("*.actual"))
        if not actual_files:
            print(green("[INFO] No .actual snapshot files to remove."))
        else:
            for f in actual_files:
                f.unlink()
                print(f"[INFO] Removed {f}")
            print(green(f"[SUCCESS] Removed {len(actual_files)} .actual files."))
