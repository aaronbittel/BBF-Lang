from __future__ import annotations

import subprocess
import textwrap
from itertools import batched
from pathlib import Path


def define_ast(
    output_dir: Path,
    classname: str,
    types: list[str],
    extra_imports: list[str] | None = None,
) -> None:
    extra_imports = extra_imports if extra_imports is not None else []
    path = output_dir / f"{classname.lower()}.py"
    with path.open(mode="w") as f:
        f.write(
            textwrap.dedent("""\
            from __future__ import annotations

            from abc import ABC, abstractmethod
            from dataclasses import dataclass
            from types import Protocol
            from typing import TYPE_CHECKING
            from bbf.lexer import Token
            """)
        )

        for extra_import in extra_imports:
            f.write(f"{extra_import}\n")

        if classname != "Expr":
            f.write("from bbf.nodes.expr import Expr\n")
        f.write("if TYPE_CHECKING:\n")
        f.write("\n    from bbf.nodes.visitor import Visitor\n")

        f.write(
            textwrap.dedent(f"""
            class {classname}(ABC):
                @abstractmethod
                def accept(self, visitor: Visitor) -> None: ...
        """)
        )

        for t in types:
            name, *members = t.split()
            is_helper = False
            if name == "Helper":
                name, *members = members
                is_helper = True
            assert len(members) % 2 == 0, f"{name}: each member must have a type"

            f.write(
                textwrap.dedent(f"""
            @dataclass
            class {name}({classname if not is_helper else ""}):
            """)
            )
            for m_name, m_type in batched(members, n=2):
                f.write(f"    {m_name}: {m_type}\n")
            if not is_helper:
                f.write("    def accept(self, visitor: Visitor) -> None:")
                f.write(f"        return visitor.visit_{name.lower()}(self)")


def define_visitor(output_dir: Path, all_types: list[tuple[str, list[str]]]) -> None:
    path = output_dir / "visitor.py"
    with path.open("w") as f:
        f.write("from typing import Protocol\n")
        for types in all_types:
            name, ts = types
            for t in ts:
                f.write(f"from bbf.nodes.{name.lower()} import {t}\n")
        f.write("\nclass Visitor(Protocol):\n")
        for types in all_types:
            name, ts = types
            for t in ts:
                f.write(
                    f"    def visit_{t.lower()}(self, {t.lower()}: {t}) -> None: ...\n"
                )


if __name__ == "__main__":
    print("I changed stuff")
    exit()
    basepath = Path("./src/bbf/nodes/")
    expr_types = (
        "Expr",
        [
            "Identifier token Token",
            "IntegerLit token Token",
            "StringLit token Token",
            "Binary lhs Expr operator Token rhs Expr",
            "Unary operator Token expr Expr",
            "Grouping expr Expr",
            "Argv expr Expr",
            "FnCall name Token args_list list[Expr]",
        ],
    )
    stmt_types = (
        "Stmt",
        [
            "IfStmt condition Expr if_block Block elifs list[ElifStmt] else_block Block|None=None",
            "ForStmt loop_ident Token range Range block Block",
            "DoBlock block Block",
            "Declaration name Token vartype Token expr Expr",
            "Assignment name Token expr Expr",
            "ExpressionStmt expr Expr",
            "Helper ElifStmt condition Expr block Block",
            "Helper Block stmts list[Stmt]=field(default_factory=list)",
            "Helper Range start Expr stop Expr inclusive bool",
        ],
    )
    toplevel_types = (
        "TopLevel",
        [
            "FunctionDefinition name Token params list[Param] return_type Token body Block",
            "TopLevelStatement stmt Stmt",
            "Helper Param name Token vartype Token",
        ],
    )
    program_types = (
        "Program",
        ["ProgramTopLevelStatement stmts list[TopLevel]"],
    )
    define_ast(output_dir=basepath, classname="Expr", types=expr_types[1])
    define_ast(
        output_dir=basepath,
        classname="Stmt",
        types=stmt_types[1],
        extra_imports=["from dataclasses import field"],
    )
    define_ast(
        output_dir=basepath,
        classname="TopLevel",
        types=toplevel_types[1],
        extra_imports=[
            "from bbf.nodes.stmt import Block",
            "from bbf.nodes.stmt import Stmt",
        ],
    )
    define_ast(
        output_dir=basepath,
        classname="Program",
        types=program_types[1],
        extra_imports=["from bbf.nodes.toplevel import TopLevel"],
    )

    all_types_names = []
    for types in [expr_types, stmt_types, toplevel_types]:
        name, members = types
        t = [member.split()[0] for member in members if member.split()[0] != "Helper"]
        all_types_names.append((name, t))

    define_visitor(basepath, all_types_names)

    subprocess.run(args="uv tool run ruff format src/bbf/nodes".split())
    subprocess.run(args="uv tool run ruff check --fix src/bbf/nodes".split())
