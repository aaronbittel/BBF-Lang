all: output

BIN_DIR = ./bin
FILENAME = test01

output:
	@uv run bbf $(FILENAME).bbf --step output

typecheck:
	@uv run bbf $(FILENAME).bbf --step typecheck

parser:
	@uv run bbf $(FILENAME).bbf --step parser

lexer:
	@uv run bbf $(FILENAME).bbf --step lexer

run: output
	@$(BIN_DIR)/$(FILENAME)

debug: output
	@gdb -q $(BIN_DIR)/$(FILENAME)

test:
	@uv run snapshot.py all

fix:
	@uv tool run ruff check --fix .
	@uv run mypy . --check-untyped-defs

.PHONY = run output parser lexer debug typecheck
