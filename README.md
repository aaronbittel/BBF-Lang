# BBF-Lang

`BBF` is my own compiled, statically-typed programming language, written in Python. The
main goal of this project is to learn compiler design and have fun experimenting with
language features. One personal goal is to solve some of the [Advent of Code
2025](https://adventofcode.com/) challenges using BBF—let's see how far I can get!


## Requirements
- `Python 3.12`
- `nasm` (Netwide Assembler)
- `ld` (GNU Linker)


## Installation
```bash
git clone https://github.com/aaronbittel/BBF-Lang.git
cd BBF-Lang
```


## Usage
```bash
# Compiles `file.bbf` and generates `bin/file` executable
uv run bbf file.bbf
```

```bash
# After succesful compilation, runs `bin/file` with arguments arg1, arg2
uv run bbf file.bbf --run arg1 args2
```

```bash
# Prints the tokens of `file.bbf` and exits with 0.
uv run bbf file.bbf --step lexer
```
- All available steps are: `lexer`, `parser`, `typecheck` and `output`


## Syntax / Language Features

- The full language
[`grammar`](https://github.com/aaronbittel/BBF-Lang/blob/main/docs/grammar.typ) is
available.
    - If you have [typst](https://github.com/typst/typst) installed you can generate the
    pdf using: `typst compile docs/grammar.typ`

### Variable Declaration

```elixir
x: Int = 12
str: String = "Hello, World!\n"
```
- Variables can be redeclared with a new type or value:

```elixir
x: Int = 42
x: Int = 51               # (new variable of type Int)
x: String = "New Type"    # (new variable of type String)
```

### Variable Assignment
```elixir
x: Int = 12
x = 24
```

### Arrays
```python
x: Int[4] = [1, 2, 3, 4]
y: Int = x[1]
```

### If
```elixir
if argc > 1 then
    stdout(argv[1]) stdout("\n")
elif argc == 1 then
    stderr("USAGE: ") stderr(argv[0]) stderr(" <arg>\n")
else
    stderr("I MESSED UP\n")
end
```
- `argc` is a global variable that tracks the number of command-line arguments.
- `argv[i]` is currently a special syntax / from of an expression that returns the
string of that `argv`. Arrays or other indexing of variables is currently not supported.

### For
```elixir
for i in 1..10 do
    stdout(itoa(i)) stdout("\n")
end
```
- Loop over a range (`start`..`stop`) by default stop is exclusive
- Inclusive ranges can be specified with `1..=10`
- Both `start` and `stop` can be expressions that evaluate to an Int

### Functions
```elixir
fn repeat(x: Int, y: String) -> Void do
    for i in 1..=x do
        stdout(y)
    end
    return # optional in this case
end
```
- Functions can return `Void` or any supported type.

### Comments
```python
# all comments are single line comments starting with `#`
x: Int = 12 # they can also be inline
```

### VarTypes
- `Int`: 64bit integer
- `String`: Strings are represented internally as a struct with length and pointer. Not
null-terminated.
- `Bool`: 64bit integer (internally)
    - Booleans are represented as integers (0 == `false`, 1 == `true`)
- `Array`: Contiguous space, stored as ptr + len
    - If defined in "global" scope, then store in `.data` section
    - If defined in "local" scope (e.g. return by a function) then stored on the stack
- `Void`: Only used in return type annotations. `x: Void = 1` is not supported

### Builtin Functions
- `exit(exitcode: Int) -> Void`: Exit program with exitcode
- `atoi(str: String) -> Int`: Convert String to Int
- `itoa(x: Int) -> String`: Convert Int to String
- `btoa(x: Int) -> String`: Convert Bool to String
- `stdout(str: String) -> Void`: Print str to stdout
- `stderr(str: String) -> Void`: Print str to stderr

## Examples / Playground

You can find a folder `/examples` in this repository with multiple `.bbf` files.

For instance, to run an example:

```bash
uv run bbf examples/isprime.bbf --run <argv>
```

## Useful Ressources
- [Tsoding
Porth](https://www.youtube.com/watch?v=-gIWxGQkIJo&list=PLpM-Dvs8t0VbMZA7wW9aR3EtBqe2kinu4): Assembly & Snapshot testing
- [intectum
Bangalang](https://www.youtube.com/watch?v=dSHXL844HKk&list=PLHIUSiAG6lLqw7Q80-v7QRXe1vd_IYRLc): Assembly, Compiler, Grammar
- [Pixeled Create a Compiler Series](https://www.youtube.com/watch?v=vcSijrRsrY0):
Assembly & Compiler
- [Mxy Youtube Channgel](https://www.youtube.com/@LearnWithMxy): Assembly
- [Kay Lack](https://www.youtube.com/@neoeno4242): Assembly
    - [Just enough assembly to blow your
    mind](https://www.youtube.com/watch?v=GU8MnZI0snA)
    - [Assembly follow-up: from ARM64 to
    x86-64](https://www.youtube.com/watch?v=feqD9k0Inds)
    - [Fast and Beautiful Assembly](https://www.youtube.com/watch?v=ON9vuzLiGuc)
- [Robert Nystrom's Crafting Interpreters](https://craftinginterpreters.com/):
Grammar Definition, Parsing Expressions, Visitor Pattern
- [X86 Instruction Reference](https://www.felixcloutier.com/x86/)
- [Linux Syscalls
Reference](https://chromium.googlesource.com/chromiumos/docs/+/master/constants/syscalls.md)


## Project Name

The name `BBF` stands for `BEST BY FAR`. It originates from a League of Legends
interview about 10 years ago: the professional player Forg1ven was asked if he was the
best ADC in Europe, and he simply replied, "By far". Inspired by this, I adopted the
in-game name `BEST BY FAR` as a joke. Later, when I needed a name for my programming
language, I decided to reuse it — hence, `BBF`.

[Original Clip](https://youtu.be/0IWojm7QngI?si=QySOzA0VjrXt55uN&t=9)

## License

This project is licensed under the [MIT License](LICENSE).
