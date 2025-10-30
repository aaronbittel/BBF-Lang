all: generation

BIN_DIR = ./bin
FILENAME = test01

generation:
	@uv run bbf generation $(FILENAME).bbf

parser:
	@uv run bbf parser $(FILENAME).bbf

lexer:
	@uv run bbf lexer $(FILENAME).bbf

debug: generation
	@gdb -q $(BIN_DIR)/$(FILENAME)

.PHONY = generation parser lexer debug
