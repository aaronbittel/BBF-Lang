import sys

from bbf.ast_printer import ASTPrinter
from bbf.cli import parse_cli_args
from bbf.runner import Step, generate_exe, parse, tokenize
from bbf.token import dump_tokens
from bbf.type_checker import TypeChecker
from bbf.utils import blue, run_cmd


def main() -> None:
    args = parse_cli_args()
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
            print(blue("[INFO]"), f"Successfully type checked `{args.filepath}`")
        if args.step == Step.TypeCheck:
            sys.exit(0)

    exe_path = args.output / args.filepath.stem if args.output.is_dir() else args.output
    generate_exe(
        prog, exe_path=exe_path, buffer_size=args.buffer_size, verbose=args.verbose
    )
    if not args.quiet:
        print(blue("[INFO]"), f"Successfully compiled program to `{exe_path}`")

    if args.run is not None:
        run_args = [str(exe_path), *args.run]
        run_res = run_cmd(run_args, echo=args.verbose, capture_output=False)
        sys.exit(run_res.returncode)


if __name__ == "__main__":
    main()
