# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Color diff for snapshot testing
- Bool Type, `true` and `false` literals
- Boolean Operators `or` and `and` (Currently using Complete Boolean Evaluation)

### Changed

- snapshot.py `update` command will reuse the previous argv if none is given

### Fixed

- Improved parser error messages for invalid declarations/assignments:
  `true: Int = 0` or `false = 1` now produce clear errors instead of cryptic messages.

## 0.2.0 – 2025-10-29

### Added

- Lexer, Parser, Typechecking and Assembly Code Generator
- Cli for running compiler
- snapshot.py for testing
