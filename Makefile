all: gen

BIN_DIR = ./bin
FILENAME = test01

gen:
	@uv run bbf gen $(FILENAME).bbf

parser:
	@uv run bbf parser $(FILENAME).bbf

lexer:
	@uv run bbf lexer $(FILENAME).bbf

debug: gen
	@gdb -q $(BIN_DIR)/$(FILENAME)

.PHONY = gen parser lexer debug
