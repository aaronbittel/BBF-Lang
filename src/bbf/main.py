import subprocess
import sys
from pathlib import Path
from typing import Literal

from bbf.generation import CodeGenerator
from bbf.lexer import Lexer, Token, TokenType, dump_tokens
from bbf.parser import Parser
from bbf.utils import eprint, green, red

# TODO: Use snapshot testing


type Step = Literal["lexer", "parser", "generation"]


def main() -> None:
    if len(sys.argv) == 1:
        eprint("usage: uv run bbf [mode=generation] <input.bbf>")
        sys.exit(1)

    step: Step = "generation"
    if len(sys.argv) == 3:
        step, input_path = sys.argv[1], Path(sys.argv[2])
    else:
        input_path = Path(sys.argv[1])

    with input_path.open(mode="r") as f:
        input_content = f.read()
    print(f"[INFO] Read input file: {input_path}")
    print(input_content)
    print("=====================")

    lexer = Lexer(path=input_path, src=input_content)
    tokens: list[Token] = []
    while (token := lexer.next_token()) and token.ttype != TokenType.EOF:
        tokens.append(token)

    tokens.append(lexer.next_token())
    assert tokens[-1].ttype == TokenType.EOF

    print("[INFO] Parsed into Tokens:")
    dump_tokens(tokens)
    print("=====================")

    if step == "parser" or step == "generation":
        print("[INFO] Parsed into:")
        parser = Parser(tokens)
        prog = parser.parse_program()
        print(prog)
        print("=====================")

        if step == "generation":
            output_path = Path(f"./bin/{input_path.stem}.asm")
            code_gen = CodeGenerator(prog=prog)
            print(f"[INFO] Writing assembly output to {output_path}")
            code_gen.gen_prog()
            with output_path.open(mode="w") as f:
                code_gen.write_to(f)

            output_dir = output_path.parent
            out_filename = output_path.stem
            output_o = output_dir / f"{out_filename}.o"

            nasm = f"nasm -f elf64 -g -F dwarf -o {output_o} {output_path}"
            ld = f"ld -o {output_dir / out_filename} {output_o}"

            nasm_res = subprocess.run(args=nasm.split())
            print(f"[INFO] {nasm}")
            if nasm_res.returncode != 0:
                eprint(red("[ERROR] nasm Failed"))
                sys.exit(1)

            ld_res = subprocess.run(args=ld.split())
            print(f"[INFO] {ld}")
            if ld_res.returncode != 0:
                eprint(red("[ERROR] ld Failed"))
                sys.exit(1)

            print(green("[INFO] Successfully compiled!"))


if __name__ == "__main__":
    main()
