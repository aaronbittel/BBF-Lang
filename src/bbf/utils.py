import sys
from functools import partial

eprint = partial(print, file=sys.stderr)

RED = "\033[91m"
GREEN = "\033[92m"
BLUE = "\033[94m"
RESET = "\033[0m"


def red(s: str) -> str:
    return f"{RED}{s}{RESET}"


def green(s: str) -> str:
    return f"{GREEN}{s}{RESET}"


def blue(s: str) -> str:
    return f"{BLUE}{s}{RESET}"
