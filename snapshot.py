#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import Generator, Literal, NamedTuple, TextIO

from bbf.ast_printer import ASTPrinter
from bbf.lexer import Token
from bbf.nodes.program import ProgTopLevelStmt
from bbf.runner import Step, generate_exe, parse, tokenize
from bbf.type_checker import TypeChecker, TypeCheckerError
from bbf.utils import blue, darkgray, eprint, green, red, run_cmd

# TODO: print diffs on fail


SNAPSHOTS_DIR = Path("./tests/snapshots/")
SNAPSHOTS_DIR.mkdir(exist_ok=True, parents=True)
CASES_DIR = Path("./tests/cases/")
CASES_DIR.mkdir(exist_ok=True, parents=True)
EXAMPLES_DIR = Path("./examples/")
EXAMPLES_DIR.mkdir(exist_ok=True, parents=True)
TMP_DIR = Path("/tmp", "bbf")
TMP_DIR.mkdir(exist_ok=True, parents=True)


@dataclass
class RunStats:
    run_count: int = 0
    succeeded: int = 0
    failed_files: list[TestOutcome] = field(default_factory=list)
    skipped_files: list[TestOutcome] = field(default_factory=list)

    def fail(self, filepath: Path, step: Step, reason: str) -> None:
        assert step is not Step.All
        self.run_count += 1
        self.failed_files.append(TestOutcome(filepath, step, reason))

    def skip(self, filepath: Path, step: Step, reason: str) -> None:
        assert step is not Step.All
        self.run_count += 1
        self.skipped_files.append(TestOutcome(filepath, step, reason))

    def success(self) -> None:
        self.run_count += 1
        self.succeeded += 1

    def __str__(self) -> str:
        assert self.run_count == self.succeeded + len(self.failed_files) + len(
            self.skipped_files
        ), (
            f"messedup counting: {self.run_count = } {self.succeeded = } + {len(self.failed_files) = } + {len(self.skipped_files) = }"
        )
        return (
            f"{blue('[INFO]')} RunStats — "
            f"Run {self.run_count} tests: "
            f"{green(f'{self.succeeded} success')}, "
            f"{red(f'{len(self.failed_files)} failed')}, "
            f"{darkgray(f'{len(self.skipped_files)} skipped')}."
            f"{format_outcomes(self.skipped_files, status='skip')}"
            f"{format_outcomes(self.failed_files, status='fail')}"
        )


@dataclass
class TestCase:
    argv: list[str] = field(default_factory=list)
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


class SnapshotResult(NamedTuple):
    status: Literal["success", "fail", "skip"]
    reason: str | None = None
    actual_path: Path | None = None


class RunnerResult(NamedTuple):
    step: Step
    content: str


class TestOutcome(NamedTuple):
    path: Path
    step: Step
    reason: str


class MissingArgvError(RuntimeError):
    pass


type StepStatus = Literal["success", "fail", "skip"]


def parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run snapshot tests for .bbf files")
    run_parser.add_argument(
        "step", choices=list(Step), type=Step.from_cli, nargs="?", default=Step.All
    )
    run_parser.add_argument("--path", type=Path, default=CASES_DIR)

    record_argparser = subparsers.add_parser(
        "record", help="Record snapshot for .bbf files"
    )
    record_argparser.add_argument(
        "step", choices=list(Step), type=Step.from_cli, nargs="?", default=Step.All
    )
    record_argparser.add_argument("--path", type=Path, default=CASES_DIR)
    record_argparser.add_argument("--argv", nargs="*", default=[])

    update_parser = subparsers.add_parser(
        "update", help="update snapshot for .bbf files"
    )
    update_parser.add_argument(
        "step", choices=list(Step), type=Step.from_cli, nargs="?", default=Step.All
    )
    update_parser.add_argument("--path", type=Path, default=CASES_DIR)
    update_parser.add_argument("--argv", nargs="*", default=[])

    all_parser = subparsers.add_parser("all", help="all snapshot for .bbf files")
    all_parser.add_argument(
        "step", choices=list(Step), type=Step.from_cli, nargs="?", default=Step.All
    )

    subparsers.add_parser("clean")
    return parser.parse_args()


def runner_gen(
    filepath: Path, argv: list[str] | None
) -> Generator[RunnerResult, None, None]:
    tokens = tokenize(filepath)
    yield RunnerResult(Step.Lexer, content=tokens_to_str(tokens))

    prog = parse(tokens)
    yield RunnerResult(Step.Parser, content=ast_to_str(prog))
    yield RunnerResult(Step.TypeCheck, content=typecheck_to_str(prog))

    exe = TMP_DIR / "out"
    generate_exe(prog, exe_path=exe)

    if argv is None:
        raise MissingArgvError

    out_res = run_cmd([str(exe), *argv], echo=False)
    tc = TestCase(
        argv, out_res.returncode, out_res.stdout.decode(), out_res.stderr.decode()
    )
    yield RunnerResult(Step.Output, testcase_to_str(tc))


def record_snapshot(command: str, step: Step, path: Path, content: str) -> None:
    snap_path = step_snapshot_path(path, step)
    if command != "record" and not snap_path.exists():
        print(
            red("[ERROR]"),
            f"No `{step}` snapshot file found for {path.name}. Use `record`.",
        )
        return
    if command == "record" and snap_path.exists():
        print(
            red("[ERROR]"),
            f"{snap_path} exists. Use `update` or `run`.",
        )
        return
    snap_path.write_text(content)
    info = "Recorded" if command == "record" else "Updated"
    print(
        blue("[INFO]"),
        f"{info} `{step}` for `{path.name}` into `{snap_path.name}`",
    )


def run_snapshot(path: Path, step: Step, got: str, stats: RunStats) -> SnapshotResult:
    snap_path = step_snapshot_path(path, step)
    if not snap_path.exists():
        return SnapshotResult(
            status="skip",
            reason=f"No `{step}` snapshot file found for {path.name}. Use `record`.",
        )
    expected = snap_path.read_text()
    if expected != got:
        stats.fail(path, step, reason="Output mismatch")
        actual_path = Path(str(snap_path) + ".actual")
        actual_path.write_text(got)
        return SnapshotResult("fail", reason="Output mismatch", actual_path=actual_path)
    return SnapshotResult(status="success")


def record_dir(command: str, step: Step, dirpath: Path, argv: list[str]) -> None:
    for filepath in dirpath.rglob("*.bbf"):
        record_file(command, step, filepath, argv)


def record_file(command: str, step: Step, filepath: Path, argv: list[str]):
    runner = runner_gen(filepath, argv)
    try:
        for result in runner:
            if step != step.All and result.step != step:
                continue
            record_snapshot(command, result.step, filepath, result.content)
            if result.step == step:
                break
    except MissingArgvError:
        assert False, "unreachable"
    except RuntimeError as e:
        print(red("[ERROR]"), str(e))


def run_dir(step: Step, dirpath: Path, stats: RunStats) -> None:
    for filepath in dirpath.rglob("*.bbf"):
        run_file(step, filepath, stats)


def run_file(step: Step, filepath: Path, stats: RunStats) -> None:
    argv = None
    out_path = step_snapshot_path(filepath, Step.Output)
    if step == Step.Output or step == Step.All:
        if out_path.exists():
            argv = load_test_case(out_path).argv

    runner = runner_gen(filepath, argv)
    try:
        for result in runner:
            if step != Step.All and step != result.step:
                continue
            res = run_snapshot(filepath, result.step, result.content, stats)
            match res:
                case SnapshotResult(
                    status="fail", reason=reason, actual_path=actual_path
                ):
                    assert reason is not None
                    stats.fail(filepath, step, reason)
                    print(
                        red("[FAILED]"),
                        f"Running `{result.step}` for `{filepath.name}`",
                        f"- {reason}",
                    )
                    assert actual_path is not None
                    print(f"         Saved actual to `{actual_path.name}`")
                case SnapshotResult(status="skip", reason=reason):
                    assert reason is not None
                    stats.skip(filepath, result.step, reason=reason)
                    print(
                        darkgray("[SKIPING]"),
                        f"Running `{result.step}` for `{filepath.name}`",
                    )
                    print(f"          {reason}")
                case SnapshotResult(status="success"):
                    stats.success()
                    print(
                        green("[SUCCESS]"),
                        f"Running `{result.step}` for `{filepath.name}`",
                    )
            if result.step == step:
                return
    except MissingArgvError:
        msg = "Missing snapshot. Use `record`."
        stats.skip(filepath, Step.Output, msg)
        print(
            darkgray("[SKIPING]"),
            f"Missing `output` snapshot for `{filepath.name}`",
        )
    except RuntimeError as e:
        print("runtime", repr(str(e)))
        stats.skip(filepath, Step.Output, str(e))
        print(darkgray("[SKIPING]"), str(e))


def tokens_to_str(tokens: list[Token]) -> str:
    return "\n".join(
        f"{t.ttype}[{t.position.line}:{t.position.column}] => {t.value!r}"
        for t in tokens
    )


def ast_to_str(prog: ProgTopLevelStmt) -> str:
    buf = StringIO()
    prog.accept(ASTPrinter(buf))
    return buf.getvalue()


def typecheck_to_str(prog: ProgTopLevelStmt) -> str:
    try:
        prog.accept(TypeChecker())
        status = "OK"
    except TypeCheckerError as e:
        status = str(e)
    return status


def testcase_to_str(testcase: TestCase) -> str:
    # TODO: handle "alsdjf lsfdj" input
    out = f"Argv: {len(' '.join(testcase.argv))}\n"
    out += f"{' '.join(testcase.argv)}\n"
    out += f"Returncode: {len(str(testcase.returncode))}\n"
    out += f"{testcase.returncode}\n"
    out += f"Stdout: {len(testcase.stdout)}\n"
    out += f"{testcase.stdout}\n"
    out += f"Stderr: {len(testcase.stderr)}\n"
    out += f"{testcase.stderr}\n"
    return out


def load_test_case(filepath: Path) -> TestCase:
    tc = TestCase()
    with filepath.open(mode="r") as f:
        argv = parse_line(f, "Argv")
        tc.argv = argv.split(" ") if argv != "" else []
        tc.returncode = int(parse_line(f, "Returncode"))
        tc.stdout = parse_line(f, "Stdout")
        tc.stderr = parse_line(f, "Stderr")
    return tc


def parse_line(f: TextIO, ttype: str) -> str:
    try:
        line = f.readline()
        t, len_str = line.split(": ")
    except ValueError:
        raise
    assert t == ttype
    content = f.read(int(len_str))
    assert f.read(1) == "\n"
    return content


def step_snapshot_path(path: Path, step: Step) -> Path:
    assert step is not Step.All, (
        f"`step_snapshot_path()` is not allowed to take `{step}`"
    )
    return (SNAPSHOTS_DIR / path.stem).with_suffix(f".{step.ext}.snap")


def format_outcomes(outcomes: list[TestOutcome], status: StepStatus) -> str:
    if len(outcomes) == 0:
        return ""

    if status == "fail":
        out = f"\n{red('Failed Files:')}\n"
    elif status == "skip":
        out = f"\n{darkgray('Skipped Files:')}\n"
    else:
        assert False, "unreachable"

    out += "\n".join(f"  `{out.path}`[{out.step}] -- {out.reason}" for out in outcomes)
    return out


def should_confirm_argv(argv: list[str]) -> bool:
    for arg in argv:
        if arg in ("lexer", "parser", "typecheck", "output", "all"):
            return True
    return False


def check_argv(command: str, step: Step, argv: list[str]) -> None:
    if should_confirm_argv(argv):
        answer = input(f"Did you mean to call `{command} {step}` with `{argv}`? [Y/n] ")
        if answer.lower() not in ("y", "yes"):
            print("Aborting ...")
            sys.exit(0)


if __name__ == "__main__":
    args = parse_cli_args()
    if args.command in ("record", "update"):
        check_argv(args.command, args.step, args.argv)
        if args.path.is_file():
            record_file(args.command, args.step, args.path, args.argv)
        elif args.path.is_dir():
            record_dir(args.command, args.step, args.path, args.argv)
        else:
            eprint(f"`{args.path}` does not exist.")
            sys.exit(1)
    elif args.command == "run":
        stats = RunStats()
        if args.path.is_file():
            run_file(args.step, args.path, stats)
        elif args.path.is_dir():
            run_dir(args.step, args.path, stats)
        else:
            eprint(f"`{args.path}` does not exist.")
            sys.exit(1)
        print("=" * 90)
        print(stats)
    elif args.command == "all":
        stats = RunStats()
        run_dir(Step.All, CASES_DIR, stats)
        run_dir(Step.All, EXAMPLES_DIR, stats)
        print("=" * 90)
        print(stats)
    elif args.command == "clean":
        for filepath in SNAPSHOTS_DIR.rglob("*.actual"):
            filepath.unlink()
            print(blue("[INFO]"), f"Deleted `{filepath}`")
    else:
        print(red("[ERROR]"), f"Unknown command `{args.command}`")
        sys.exit(1)
