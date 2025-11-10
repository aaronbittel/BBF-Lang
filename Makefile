all: gen

BIN_DIR = ./bin
FILENAME = test01

gen:
	@uv run bbf $(FILENAME).bbf --step gen

parser:
	@uv run bbf $(FILENAME).bbf --step parser

lexer:
	@uv run bbf $(FILENAME).bbf --step lexer

debug: gen
	@gdb -q $(BIN_DIR)/$(FILENAME)

.PHONY = gen parser lexer debug
