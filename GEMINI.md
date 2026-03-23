# Gemini Workspace Configuration

Read "./README.md" for all instructions.
Use `poetry run cb` instead of just running `./cb.py`
Use `poetry run help` to gather all details.

# Style Guide
- You must follow the google style guide for python coding.
- Do **not** use non-local imports inside classes or methods.
- You must not skip pylint checks.
- Check surrounding code and class hierarchies for reusing functionality.
- Use existing tests and test classes to write platform and mock tests.

## Platform Code
- Avoid using raw shell-commands if possible and directly use the platform
  helpers for the same functionality.
- Avoid using "shell = True", eiher use or extend the explicit platform
  helpers or look for simple workarounds.
- New platform methods should be implemented in the most abstract platform
  class if possible.

## Paths
- Use pth.AnyPath or pth.LocalPath instead of strings for paths.
- Use pth.AnyPath for paths that can either be local and/or remote.
- Use pth.LocalPath for paths that are exclusively local.

## Input Parsing
- All user input should pass through one of the helpers from
  `crossbench.parse`.
- Do early input validation either in the config parser or argument parsing.
- Any new parser helper method needs a dedicated unittest.

## ConfigObjects
- Any complex input parameter should be a dedicated immutable / frozen
  ConfigObject with proper documentation.
- Add unittests for each newly added ConfigObject.
- Add example config files to the config/doc or a better suited
  config/* folder.

# Sanity Checks
- Always do `poetry run ruff check` after completing a change to validate
all results.
- Run `poetry run mypy crossbench` after finishing a larger change.
- Run tests with `poetry run pytest tests/crossbench -x -n 7`
