all: build run

BIN_DIR = ./bin
FILENAME = test01

run: compile p
	@$(BIN_DIR)/$(FILENAME)

p: p.o
	@ld -o $(BIN_DIR)/$(FILENAME) $(BIN_DIR)/$(FILENAME).o

p.o:
	@nasm -f elf64 -g -F dwarf -o $(BIN_DIR)/$(FILENAME).o $(BIN_DIR)/$(FILENAME).asm

compile:
	@uv run bbf com $(FILENAME).bbf

tokenize:
	@uv run bbf tok $(FILENAME).bbf
