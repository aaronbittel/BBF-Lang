all: gen

BIN_DIR = ./bin
FILENAME = test01

gen:
	@uv run bbf $(FILENAME).bbf --step gen

parser:
	@uv run bbf $(FILENAME).bbf --step parser

lexer:
	@uv run bbf $(FILENAME).bbf --step lexer

run: gen
	@$(BIN_DIR)/$(FILENAME)

debug: gen
	@gdb -q $(BIN_DIR)/$(FILENAME)

.PHONY = run gen parser lexer debug
