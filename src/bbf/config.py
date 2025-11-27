from pathlib import Path

BIN_DIR = Path("./bin")
BIN_DIR.mkdir(parents=True, exist_ok=True)

GLOBAL_BUFFER_CAPACITY = 1024 * 1024
