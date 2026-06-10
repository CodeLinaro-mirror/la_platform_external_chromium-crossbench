---
name: Crossbench Python Style
description: Guidelines for writing high-quality Python code in Crossbench, focusing on custom design patterns, platform abstractions, and rules not covered by Ruff.
---

# Crossbench Python Style & Best Practices

This skill provides guidelines and patterns for writing Python code in the
Crossbench codebase. These rules cover architectural patterns, custom
abstractions, and design guidelines that are **not** automatically enforced by
Ruff.

For standard linting always rely on `poetry run ruff check`.

## Strict Import Discipline

- Imports must only happen at top-level

Importing modules locally inside classes or methods is **strictly forbidden**.
All imports must reside at the top level of the file.

```python
# BAD - Forbidden local import
class MyProbe(Probe):
  def setup(self) -> None:
    import subprocess  # FORBIDDEN

# GOOD - Clean top-level import
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
# BAD
import subprocess
subprocess.run(["cp", src, dest])

# GOOD
self.host_platform.symlink_or_copy(src, dest)
```

If a new platform capability is needed, implement it in the most abstract
platform base class (`Platform`) rather than writing platform-specific scripts
directly.

______________________________________________________________________

## Input Validation & `ConfigObject`s

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
- Every new `ConfigObject` or parsing helper **must** have dedicated unit tests.

### ConfigParser & `add_default_argument`

When implementing configuration parsing for a probe or component via
`config_parser()`, you can allow users to specify configuration using a compact
string shorthand (e.g., `--probe=v8.log:all`) instead of requiring full
dictionary/HJSON syntax (`--probe=v8.log:{categories: ['all']}`) by using
`parser.add_default_argument(...)`. This default argument is then automatically
used by `parse_str` .

______________________________________________________________________

## Design Patterns

- **Short Methods**: Keep methods short and break them into well-named helper
  functions.
- **Reusability**: Check surrounding code and class hierarchies before
  implementing new functionality; reuse existing methods.

______________________________________________________________________

## Sanity Checks & Verification

Before committing or uploading changes, always run the validation suite:

1. **Mypy Type Checker:** `poetry run mypy crossbench`
2. **Unit Tests:** `poetry run pytest tests/crossbench -x -n 7`
3. **Crossbench Invocation:** Use `poetry run cb` instead of executing `./cb.py`
   directly.
