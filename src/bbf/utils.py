import sys
from functools import partial

eprint = partial(print, file=sys.stderr)

RED = "\033[91m"
RESET = "\033[0m"


def red(s: str) -> str:
    f"{RED}{s}{RESET}"
