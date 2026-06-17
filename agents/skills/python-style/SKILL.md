---
name: Crossbench Python Style
description: Guidelines for writing high-quality Python code in Crossbench, focusing on custom design patterns, platform abstractions, and rules not covered by Ruff.
---

# Crossbench Python Style & Best Practices

This skill provides guidelines and patterns for writing Python code in the
Crossbench codebase. These rules cover architectural patterns, custom
abstractions, and design guidelines that are **not** automatically enforced by
Ruff.

## Linting with ruff:

For standard linting always rely on `vpython3 -m ruff check` and use
`vpython3 -m ruff check --fix`.

Avoid adding skip rules like `# noqa: BLE001` but rather fix the surrounding
code and look for better approaches.

## Formatting:

- Do not use `ruff format`
- Use `git cl format` to format all sources

## Strict Import Discipline

- Imports must only happen at top-level

Importing modules locally inside classes or methods is **strictly forbidden**.
All imports must reside at the top level of the file.

```python
# BAD: Forbidden local import
class MyProbe(Probe):
  def setup(self) -> None:
    import subprocess  # FORBIDDEN

# GOOD: Clean top-level import
import subprocess
```

## Path Abstraction (`crossbench.path`)

To ensure cross-platform compatibility (e.g., Linux, macOS, Windows, Android,
ChromeOS), **never use raw strings for file or directory paths**. While Ruff
encourages `pathlib`, Crossbench requires using its own specialized path classes
outside the raw platform methods.

### Import Path Namespace

Always import the path module with the `pth` alias this helps with testing when
using pyfakefs which needs to monkey patch `pathlib` classes:

```python
from crossbench import path as pth
```

### `LocalPath` vs. `AnyPath`

- **`pth.LocalPath`**: Use for paths that are exclusively local to the host
  running the script.
- **`pth.AnyPath`**: Use for paths that can represent either local or remote
  locations (such as a path on an Android device, a remote SSH target).

```python
# Local file manipulation
def save_log(self, log_dir: pth.LocalPath) -> pth.LocalPath:
  log_file = log_dir / "output.txt"
  return log_file
```

## Platform & Command Abstractions

Direct shell execution creates fragile, non-portable code. Crossbench abstracts
system commands through `Platform` objects.

- **Never** use raw shell-commands (e.g., `subprocess.run`, `os.system`).
- **Strictly avoid** use `shell=True` unless there is no other workaround.
- Use the appropriate platform helper (`self.host_platform` or the target
  browser's platform) to perform system operations:

```python
# BAD: raw shell command only running on the local host
import subprocess
subprocess.run(["cp", src, dest])

# GOOD: high-level file helper that works in any platform
self.host_platform.symlink_or_copy(src, dest)
```

If a new platform capability is needed, implement it in the most abstract
platform base class (`Platform`) rather than writing platform-specific scripts
directly.

## Binary Lookup

Use `path_finder.py` helpers to look up non-default binaries that might be in
different places on the system. Using custom finder helpers makes the code more
robust on different platforms.

- Prefer using binaries provided with a chromium checkout
- Use subclasses of BasePathFinder to implement more complex binary lookups if
  they are not available on the default system paths by default

```
# BAD: hardcoded non-standard binary path
self.platform.sh("path/to/custom/binary", "--test=foo")

# GOOD: abstract finder
binary = CustomBinaryFinder(self.platform).local_path
self.platform.sh(binary, "--test=foo")
```

______________________________________________________________________

## Input Validation & `ConfigObject`

All user-facing or configurable inputs must follow strict parsing patterns to
catch issues early.

### Early Input Validation

- Pass all user input through validation helpers in `crossbench.parse`.
- Perform input validation at the boundary (config parsing or argument parsing).

### Dedicated `ConfigObject`

- Any complex input parameter should be modelled as a dedicated, immutable /
  frozen `ConfigObject`.
- Provide comprehensive documentation and example configurations in
  `config/doc/` or under `config/*`.
- Every new `ConfigObject` or parsing helper **must** have dedicated unit tests
  covering short form parsing and full dict inputs.

### ConfigParser & `add_default_argument`

When implementing configuration parsing for a probe or component via
`config_parser()`, you can allow users to specify configuration using a compact
string shorthand (e.g., `--probe=v8.log:all`) instead of requiring full
dictionary/HJSON syntax (`--probe=v8.log:{categories: ['all']}`) by using
`parser.add_default_argument(...)`. This default argument is then automatically
used by `parse_str` .

______________________________________________________________________

## Design Patterns and style

- **Short Methods**: Keep methods short and break them into well-named helper
  functions.
- **Reusability**: Check surrounding code and class hierarchies before
  implementing new functionality; reuse existing methods.
- **Code Duplication**: Add reusable methods for repeated code snippets.
- **Walrus Operator**: Use the walrus operator for simple code
  ```
  # BAD:
  log_path = browser.log_path
  if log_path:
    self.do_stuff(log_path)

  # GOOD: compact use of walrus operator
  if log_path := browser.log_path:
    self.do_stuff(log_path)
  ```
- **Early Returns**: Use early returns, continue and breaks to reduce nesting
  levels. It's ok to duplicate simple return statements. Prefer separate early
  bailout checks.
  ```
  # BAD: nested long blocks
  def foo(value):
    if value:
      if value == "error":
        return "error"
      # large block here
      ...
    return "done"

  # GOOD: shallow nesting with early returns
  def foo(value):
    if not value:
      return "done"
    if value == "error":
      return "error"
    # large block here
    ...
    return "done"
  ```
- **Reduce Code Comments**: Avoid inline code comments and prefer using
  well-named constants and helper methods and helper classes. Code comments
  bit-rod, it's better to have executable documentation like tests. Comments on
  classes are good.
- **Avoid getattr and hasattr**: The methods are generally an antipattern. For
  accessing args, fix the tests first and add mock values to the test
  Namespaces.
  ```
  # BAD: getattr on args
  if browser_type := getattr(args, "browser_type"):
    ...

  # GOOD: directly accessing args attributes
  if browser_type := args.browser_type:
    ...
  ```

______________________________________________________________________

## Sanity Checks & Verification

Before committing or uploading changes, always run the validation suite:

1. **Mypy Type Checker:** `poetry run mypy crossbench`
2. **Unit Tests:** `poetry run pytest tests/crossbench -x -n 7`
3. **Crossbench Invocation:** Use `poetry run cb` instead of executing `./cb.py`
   directly.
