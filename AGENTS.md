# Gemini Workspace Configuration

Read `./README.md` for all instructions.

If running `./cb.py` fails, try the following:

1. Look for a local `depot_tools` installation and add it to `$PATH`.

2. If no `depot_tools` found, try running with `poetry`: `poetry run cb`.

# Python Code Style Guide
- You must follow the google style guide for python coding.
- local imports inside classes or methods are strictly **forbidden**.
- Check surrounding code and class hierarchies for reusing functionality.
- Use existing tests and test classes to write platform and mock tests.
- Use early returns / early control flow to reduce nesting levels.
- Keep methods short where possible and use well-named helper methods.
- Type annotate all instance methods inside __init__ methods, method arguments
  and return values.
- Always run ruff and and mypy after completing a change.

## Crossbench Platform Code
- Avoid using raw shell-commands if possible and directly use the platform
  helpers for the same functionality.
- Avoid using "shell = True", either use or extend the explicit platform
  helpers or look for simple workarounds.
- New platform methods should be implemented in the most abstract platform
  class if possible.

## Crossbench Paths
- Use pth.AnyPath or pth.LocalPath instead of strings for paths.
- Use pth.AnyPath for paths that can either be local and/or remote.
- Use pth.LocalPath for paths that are exclusively local.

## Crossbench Input Parsing
- All user input should pass through one of the helpers from
  `crossbench.parse`.
- Do early input validation either in the config parser or argument parsing.
- Any new parser helper method needs a dedicated unittest.

## Crossbench ConfigObjects
- Any complex input parameter should be a dedicated immutable / frozen
  ConfigObject with proper documentation.
- Add unittests for each newly added ConfigObject.
- Add example config files to the config/doc or a better suited
  config/* folder.

# Crossbench Sanity Checks
- When producing changes, you should run the following validations - tests, mypy, ruff.
  However, it is extremely important to run such validations at the right time only,
  because the user's time is valuable. Unless there is good reason to do otherwise,
  you should run tests first, then check mypy, and finish off with ruff. Only proceed
  to the next of these once the previous one passes without errors.
- Tests: Run tests with `vpython3 -m pytest tests/crossbench -x -n 7`.
  Working on CLs is an iterative process. Only run the relevant subset of tests
  during most iterations (e.g. only relevant files), and only run the entire suite
  when it's time to finalise a CL.
- mypy: Run `vpython3 -m mypy` only when absolutely necessary (e.g., after a larger change).
  To save time, restrict it to the minimum set of modified files rather than the
  entire codebase.
- ruff: Always do `vpython3 -m ruff check` after completing a change to validate
  all results.

# Running Performance Investigations
- **Environment Validation**: When running `cb.py` automatically, it might
  block on an interactive prompt for environment validation. Use the
  `--env-validation=warn` flag to prevent blocking while still seeing warning
  outputs.
