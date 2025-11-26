# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Builtin function `read_entire_file(filename: String)`
- String indexing
- String comparison

### Changed

- Reuse identical strings in .data section

### Fixed

## 0.4.2 - 2025-11-26

### Added

- Array Declaration (Int, Bool, String) -> `x: Int[4] = [1, 2, 3, 4]`
- Array Access -> `y: Int = x[0]`
- Array Modification -> `x[2] = 12`
- Array as Function Parameter and Return Type
- Typechecker compares each vartype of return statement to function annotated vartype

### Changed

- Only allow Void as function return type annotation (typechecker)

### Fixed

- `!=` is correctly recognized by the lexer

## 0.3.1 - 2025-11-21

### Added

- Color diff for snapshot testing
- Bool Type, `true` and `false` literals
- Boolean Operators `or` and `and`
- Short Circuit Boolean Evaluation

### Changed

- snapshot.py `update` command will reuse the previous argv if none is given

### Fixed

- Improved parser error messages for invalid declarations/assignments:
  `true: Int = 0` or `false = 1` now produce clear errors instead of cryptic messages.

## 0.2.0 – 2025-11-16

### Added

- Lexer, Parser, Typechecking and Assembly Code Generator
- Cli for running compiler
- snapshot.py for testing
