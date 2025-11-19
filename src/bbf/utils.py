import subprocess
import sys
from functools import partial
from subprocess import CompletedProcess

eprint = partial(print, file=sys.stderr)

RED = "\033[91m"
GREEN = "\033[92m"
BLUE = "\033[94m"
GRAY_DARK = "\033[90m"
RESET = "\033[0m"


def run_cmd(
    args: list[str], *, echo: bool = True, capture_output: bool = True
) -> CompletedProcess[bytes]:
    if echo:
        print(blue("[INFO]"), f"Running {' '.join(args)}")
    return subprocess.run(args, capture_output=capture_output)


def red(s: str) -> str:
    return f"{RED}{s}{RESET}"


def green(s: str) -> str:
    return f"{GREEN}{s}{RESET}"


def blue(s: str) -> str:
    return f"{BLUE}{s}{RESET}"


def darkgray(s: str) -> str:
    return f"{GRAY_DARK}{s}{RESET}"
