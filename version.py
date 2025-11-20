import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

import tomli_w as tomlw

from bbf.utils import green, run_cmd

CONFIG_PATH = Path("./pyproject.toml")


@dataclass
class Version:
    major: int
    minor: int
    patch: int

    @classmethod
    def from_str(cls, s: str) -> Self:
        major, minor, patch = map(int, s.split("."))
        return cls(major, minor, patch)

    def bump_major(self) -> None:
        self.major += 1
        self.minor = 0
        self.patch = 0

    def bump_minor(self) -> None:
        self.minor += 1
        self.patch = 0

    def bump_patch(self) -> None:
        self.patch += 1

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def read_config(filepath: Path) -> dict[str, Any]:
    with filepath.open(mode="rb") as f:
        return tomllib.load(f)


def write_config(filepath: Path, config: dict[str, Any]) -> None:
    with filepath.open(mode="wb") as f:
        tomlw.dump(config, f, indent=4)


def main() -> None:
    if len(sys.argv) == 1:
        print(f"USAGE: {sys.argv[0]} <(patch | minor | major)>", file=sys.stderr)
        sys.exit(1)

    part = sys.argv[1].lower()
    config = read_config(CONFIG_PATH)
    version = Version.from_str(config["project"]["version"])
    old_version = str(version)
    if part == "major":
        version.bump_major()
    elif part == "minor":
        version.bump_minor()
    elif part == "patch":
        version.bump_patch()
    else:
        print(f"Unknown value: {part}", file=sys.stderr)
        print(f"USAGE: {sys.argv[0]} <(patch | minor | major)>", file=sys.stderr)
        sys.exit(1)

    config["project"]["version"] = str(version)
    write_config(CONFIG_PATH, config)

    assert (
        run_cmd(["uv", "run", "bbf", "--version"], capture_output=False).returncode == 0
    )

    print(
        green(f"Successfully updated project version from {old_version} -> {version}.")
    )


if __name__ == "__main__":
    main()
