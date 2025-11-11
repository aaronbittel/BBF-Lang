from pathlib import Path
from typing import NamedTuple


class Source(NamedTuple):
    text: str
    filepath: Path
