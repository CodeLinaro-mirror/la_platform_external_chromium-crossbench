---
name: config-objects
description: Ensures inputs use crossbench.parse and complex options use immutable ConfigObjects with unit tests.
---

# Crossbench ConfigObjects & Input Parsing

This skill enforces input validation patterns and immutable configuration object
structures across Crossbench.

## Early Input Validation

- All user input and CLI/HJSON arguments must pass through validation helpers in
  `crossbench.parse`.
- Perform input validation early at the parsing boundary (config parser or
  argument parsing).
- Any new parser helper method in `crossbench.parse` **must** have a dedicated
  unit test.

## Dedicated `ConfigObject` Pattern

- Any complex or structured input parameter must be modelled as a dedicated,
  immutable / frozen `ConfigObject` (inheriting from
  `crossbench.config.ConfigObject`).
- Provide comprehensive docstrings and example configuration files in
  `config/doc/` or under `config/*`.
- Every new `ConfigObject` requires dedicated unit tests covering:
  1. Short-form string parsing (e.g. `--probe=v8.log:all`).
  2. Full dictionary/HJSON parsing (e.g.
     `--probe=v8.log:{categories: ['all']}`).

## ConfigParser & `add_default_argument`

When implementing config parsing for a probe, browser, or benchmark component
via `config_parser()`:

- Use `parser.add_default_argument(...)` to expose compact CLI shorthand syntax.
- The default argument is automatically parsed by `parse_str`.
