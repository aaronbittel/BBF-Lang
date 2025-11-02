#!/usr/bin/env python3

import subprocess
import tempfile
from bbf.utils import eprint
import argparse
from difflib import SequenceMatcher
import sys
from dataclasses import dataclass
from pathlib import Path

from bbf.generation import CodeGenerator
from bbf.lexer import Lexer
from bbf.parser import (
    Parser,
)
from bbf.utils import blue, green, red

# TODO: Record exitcode and compare exitcode

SNAPSHOTS_DIR = Path("./tests/snapshots/")
SNAPSHOTS_DIR.mkdir(exist_ok=True, parents=True)
CASES_DIR = Path("./tests/cases/")
CASES_DIR.mkdir(exist_ok=True, parents=True)


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
        f"for a specific BBF file or all files in the ./{CASES_DIR} directory."
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
        f"If omitted, all .bbf files in ./{CASES_DIR} are used."
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
    help=f"Path to the BBF file to record snapshots for. Must exist in ./{CASES_DIR}.",
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


@dataclass
class DiffLine:
    line: int
    expected: str
    actual: str


def print_diff_lines(diff_lines: list[DiffLine]) -> None:
    for diff in diff_lines:
        print(f"LINE {diff.line}: '{diff.actual}'")
        print(f"LINE {diff.line}: '{diff.expected}'")


def calculate_diff_lines(
    expected_lines: list[str], actual_lines: list[str]
) -> list[DiffLine]:
    diff_lines: list[DiffLine] = []
    for line, (expected_line, actual_line) in enumerate(
        zip(expected_lines, actual_lines)
    ):
        exp_out, act_out = highlight_diff_line(expected_line, actual_line)
        if exp_out == act_out:
            continue

        diff_lines.append(DiffLine(line=line, expected=exp_out, actual=act_out))
    return diff_lines


def highlight_diff_line(expected: str, actual: str) -> tuple[str, str]:
    """Return color-highlighted versions of expected and actual strings."""
    matcher = SequenceMatcher(None, expected, actual)
    exp_out, act_out = [], []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        exp_seg = expected[i1:i2]
        act_seg = actual[j1:j2]

        if tag == "equal":
            exp_out.append(exp_seg)
            act_out.append(act_seg)
        elif tag == "replace":
            exp_out.append(green(exp_seg))
            act_out.append(red(act_seg))
        elif tag == "delete":
            exp_out.append(green(exp_seg))
        elif tag == "insert":
            act_out.append(red(act_seg))

    return "".join(exp_out), "".join(act_out)


def lexer_snapshot_path(path: Path) -> Path:
    return (SNAPSHOTS_DIR / path.stem).with_suffix(".tok.snap")


def parser_snapshot_path(path: Path) -> Path:
    return (SNAPSHOTS_DIR / path.stem).with_suffix(".ast.snap")


def gen_snapshot_path(path: Path) -> Path:
    return (SNAPSHOTS_DIR / path.stem).with_suffix(".gen.snap")


def output_snapshot_path(path: Path) -> Path:
    return (SNAPSHOTS_DIR / path.stem).with_suffix(".out.snap")


if __name__ == "__main__":
    args = parser.parse_args()

    if args.command == "record":
        steps: list[str] = (
            ["lexer", "parser", "gen"] if "all" in args.step else args.step
        )
        path: Path = args.filepath

        if path.parent != CASES_DIR or not path.exists():
            print(red(f"ERROR: file {path} does not exist in {CASES_DIR}"))
            sys.exit(1)

        src = path.read_text()
        lexer = Lexer(path, src)
        tokens = lexer.tokenize()

        if "lexer" in steps:
            lexer_snapshot = lexer_snapshot_path(path)
            lexer_snapshot.write_text("\n".join(repr(token) for token in tokens))
            print(f"[INFO] Recorded `lexer` output for {path} into {lexer_snapshot}")

        if "parser" not in steps and "gen" not in steps:
            sys.exit(0)

        parser = Parser(tokens)
        prog = parser.parse_program()

        if "parser" in steps:
            parser_snapshot = parser_snapshot_path(path)
            parser_snapshot.write_text("\n".join(str(stmt) for stmt in prog.stmts))
            print(f"[INFO] Recorded `parser` output for {path} into {parser_snapshot}")

        if "gen" not in steps:
            sys.exit(0)

        if "gen" in steps:
            code_gen = CodeGenerator(prog)
            code_gen.gen_prog()
            gen_snapshot_asm = gen_snapshot_path(path)
            with gen_snapshot_asm.open("w", encoding="utf-8") as f:
                code_gen.write_to(f)
                # NOTE: Currently write output snapshot manually

                # with tempfile.TemporaryDirectory() as tmp_build_dir:
                #     tmp_dir = Path(tmp_build_dir)
                #     output_o = tmp_dir / "out.o"
                #     output_exe = tmp_dir / "a.out"
                #
                #     nasm = f"nasm -f elf64 -g -F dwarf -o {output_o} {gen_snapshot_asm}"
                #     ld = f"ld -o {output_exe} {output_o}"
                #
                #     print(f"[DEBUG] {nasm}")
                #     nasm_res = subprocess.run(args=nasm.split())
                #     if nasm_res.returncode != 0:
                #         eprint(red("[ERROR] nasm Failed"))
                #         sys.exit(1)
                #
                #     print(f"[DEBUG] {ld}")
                #     ld_res = subprocess.run(args=ld.split())
                #     if ld_res.returncode != 0:
                #         eprint(red("[ERROR] ld Failed"))
                #         sys.exit(1)
                #
                #     output_path = output_snapshot_path(path)
                #     exe_res = subprocess.run(args=[output_exe])
                #     output_path.write_text(str(exe_res.returncode))

                print(
                    f"[INFO] Recorded `gen` output for {path} into {gen_snapshot_asm}"
                )
                # print(f"[INFO] Recorded exitcode for {path} into {output_path}")

    elif args.command == "run":
        files_to_run = (
            [args.filepath] if args.filepath else list(CASES_DIR.glob("*.bbf"))
        )

        missing_snapshots: list[tuple[Path, str]] = []
        for path in files_to_run:
            steps: list[str] = (
                ["lexer", "parser", "gen"] if "all" in args.step else args.step
            )
            print(f"[INFO] Running tests for `{path.name}`")

            src = path.read_text()
            lexer = Lexer(path, src)
            tokens = lexer.tokenize()

            lexer_snapshot = lexer_snapshot_path(path)
            if "lexer" in steps:
                if not lexer_snapshot.exists():
                    missing_snapshots.append((path, "lexer"))
                else:
                    expected_lines = lexer_snapshot.read_text().splitlines()
                    actual_lexer_lines = [repr(token) for token in tokens]
                    diff_lines = calculate_diff_lines(
                        expected_lines, actual_lexer_lines
                    )
                    print(f"\tlexer: ", end="")
                    if len(diff_lines) == 0:
                        print(green(" [SUCCESS]"))
                    else:
                        print(red(" [FAIL]"))
                        print_diff_lines(diff_lines)
                        lexer_actual_path = lexer_snapshot.with_suffix(".actual")
                        lexer_actual_path.write_text("\n".join(actual_lexer_lines))
                        print(
                            blue(
                                f"[INFO] Saved actual `lexer` output to {lexer_actual_path}"
                            )
                        )

            if "parser" not in steps and "gen" not in steps:
                sys.exit(0)

            parser_snapshot = parser_snapshot_path(path)
            parser = Parser(tokens)
            prog = parser.parse_program()
            if "parser" in steps:
                if not parser_snapshot.exists():
                    missing_snapshots.append((path, "parser"))
                else:
                    print("\tparser: ", end="")
                    expected_lines = parser_snapshot.read_text().splitlines()
                    actual_parser_lines = [str(stmt) for stmt in prog.stmts]
                    diff_lines = calculate_diff_lines(
                        expected_lines, actual_parser_lines
                    )
                    if len(diff_lines) == 0:
                        print(green("[SUCCESS]"))
                    else:
                        print(red("[FAIL]"))
                        print_diff_lines(diff_lines)
                        parser_actual_path = parser_snapshot.with_suffix(".actual")
                        parser_actual_path.write_text("\n".join(actual_parser_lines))
                        print(
                            blue(
                                f"[INFO] Saved actual `parser` output to {parser_actual_path}"
                            )
                        )

            if "gen" not in steps:
                sys.exit(0)

            gen_snapshot_asm = gen_snapshot_path(path)
            if "gen" in steps:
                if not gen_snapshot_asm.exists():
                    missing_snapshots.append((path, "gen"))
                else:
                    print("\tgen: ", end="")
                    code_gen = CodeGenerator(prog)
                    code_gen.gen_prog()

                    expected_lines = gen_snapshot_asm.read_text().splitlines()
                    actual_gen_lines = code_gen.emitter.lines
                    diff_lines = calculate_diff_lines(expected_lines, actual_gen_lines)
                    if len(diff_lines) == 0:
                        print(green("   [SUCCESS]"))
                    else:
                        print(red("   [FAIL]"))
                        print_diff_lines(diff_lines)
                        gen_actual_path = gen_snapshot_asm.with_suffix(".actual")
                        gen_actual_path.write_text("\n".join(actual_gen_lines))
                        print(
                            blue(
                                f"[INFO] Saved actual `gen` output to {gen_actual_path}"
                            )
                        )

                with tempfile.TemporaryDirectory() as tmp_build_dir:
                    tmp_dir = Path(tmp_build_dir)
                    output_o = tmp_dir / "out.o"
                    output_exe = tmp_dir / "a.out"

                    nasm = f"nasm -f elf64 -g -F dwarf -o {output_o} {gen_snapshot_asm}"
                    ld = f"ld -o {output_exe} {output_o}"

                    nasm_res = subprocess.run(args=nasm.split())
                    if nasm_res.returncode != 0:
                        eprint(red("[ERROR] nasm Failed"))
                        sys.exit(1)

                    ld_res = subprocess.run(args=ld.split())
                    if ld_res.returncode != 0:
                        eprint(red("[ERROR] ld Failed"))
                        sys.exit(1)

                    output_path = output_snapshot_path(path)
                    exe_res = subprocess.run(args=[output_exe])
                    expected_exitcode = int(output_path.read_text().strip())
                    actual_exitcode = exe_res.returncode
                    print("\tout: ", end="")
                    if actual_exitcode != expected_exitcode:
                        print(red("   [FAIL]"))
                        print(
                            f"\tExpected exitcode of {path} to be {expected_exitcode}, but got {actual_exitcode}"
                        )
                    else:
                        print(green("   [SUCCESS]"))

        for snap, step in missing_snapshots:
            print(
                red(f"[INFO]: `{step}` snapshot for file {snap.name} does not exist.")
            )

    elif args.command == "clean":
        actual_files = list(SNAPSHOTS_DIR.glob("*.actual"))
        if not actual_files:
            print(blue("[INFO] No .actual snapshot files to remove."))
        else:
            for f in actual_files:
                f.unlink()
                print(f"[INFO] Removed {f}")
            print(blue(f"[INFO] Removed {len(actual_files)} .actual files."))
