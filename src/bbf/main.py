import sys
from pathlib import Path

from bbf.tokens import dump_tokens, tokenize
from bbf.utils import eprint
from bbf import parser
from bbf.parser import ASTNode, ASTType


def write_asm_file(output_path: Path, ast: ASTNode) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open(mode="w") as f:
        f.write("global _start\n")
        f.write("_start:\n")

        for node in ast.children:
            if node.ttype == ASTType.FunctionCall and node.value == "exit":
                f.write(f"    mov rdi, {node.children[0].value}\n")
                f.write("    call __bulitin_exit\n")

        f.write("\n")
        f.write("__bulitin_exit:\n")
        f.write("    mov rax, 60\n")
        f.write("    syscall\n")


def main() -> None:
    if len(sys.argv) == 1:
        eprint("usage: uv run bbf [mode=com] <input.bbf>")
        sys.exit(1)

    mode = "com"
    if len(sys.argv) == 3:
        mode, input_path = sys.argv[1], Path(sys.argv[2])
    else:
        input_path = Path(sys.argv[1])

    with input_path.open(mode="r") as f:
        input_file = f.read()
    print(f"Read input file: {input_path}")
    print("=====================")

    tokens = tokenize(input_path, input_file)
    print("Parsed into Tokens:")
    dump_tokens(tokens)
    print("=====================")

    if mode == "com":
        print("Parsed into FunctionCall:")
        program = parser.parse(tokens)
        print(program)
        print("=====================")

        output_path = Path(f"./bin/{input_path.stem}.asm")
        print(f"Writing assembly output to {output_path}")
        write_asm_file(output_path, program)


if __name__ == "__main__":
    main()
