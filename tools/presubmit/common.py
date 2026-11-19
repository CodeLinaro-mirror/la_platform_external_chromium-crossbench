# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
import ast
import dataclasses
import json
import pathlib
import re
import subprocess
import sys
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
  from collections.abc import Iterable, Iterator, Sequence

  from presubmit_support import AffectedFile, InputApi, OutputApi

PLACEHOLDER_BYPASS_REASONS: Final[frozenset[str]] = frozenset(
  {"todo", "tbd", "none", "n/a", "fixme", "xxx"}
)

SKIPPED_PATHS: Final[tuple[str, ...]] = (
  "third_party/*",
  "*crossbench/third_party/*",
)

# Cannot import crossbench.path.ROOT_DIR because tools/presubmit/ runs
# in-process under depot_tools' Python 3.11, whereas crossbench/path.py uses
# Python 3.12+ (PEP 695) syntax.
REPO_ROOT: Final[pathlib.Path] = pathlib.Path(__file__).resolve().parents[2]


@dataclasses.dataclass(frozen=True)
class RawAstViolation:
  line_number: int
  col_offset: int
  name: str


@dataclasses.dataclass(frozen=True)
class PythonFile:
  path: str
  content: str
  changed_lines: set[int]


@dataclasses.dataclass(frozen=True)
class AstViolation:
  file_path: str
  line_number: int
  col_offset: int
  name: str
  line_text: str

  def format_error(self) -> str:
    return (
      f"{self.file_path}:{self.line_number}:{self.col_offset}: {self.line_text}"
    )

  @classmethod
  def from_raw(
    cls,
    raw_violations: Iterable[RawAstViolation],
    python_file: PythonFile,
  ) -> list[AstViolation]:
    lines: list[str] = python_file.content.splitlines()
    return [
      cls(
        python_file.path,
        v.line_number,
        v.col_offset,
        v.name,
        lines[v.line_number - 1].strip(),
      )
      for v in raw_violations
      if v.line_number in python_file.changed_lines
    ]


class PresubmitCheck:
  def __init__(self, input_api: InputApi, output_api: OutputApi) -> None:
    self._input_api: Final[InputApi] = input_api
    self._output_api: Final[OutputApi] = output_api

  @property
  def input_api(self) -> InputApi:
    return self._input_api

  @property
  def output_api(self) -> OutputApi:
    return self._output_api

  @property
  def root_path(self) -> pathlib.Path:
    return pathlib.Path(self._input_api.PresubmitLocalPath())

  @property
  def description(self) -> str:
    return self._input_api.change.FullDescriptionText()

  @classmethod
  def is_skipped_path(cls, input_api: InputApi, file_path: str) -> bool:
    return any(
      input_api.fnmatch.fnmatch(file_path, pattern) for pattern in SKIPPED_PATHS
    )

  def affected_python_files(self, path_prefix: str = "") -> list[AffectedFile]:

    def file_filter(f: AffectedFile) -> bool:
      path: str = f.LocalPath()
      return (
        path.startswith(path_prefix)
        and path.endswith(".py")
        and not self.is_skipped_path(self._input_api, path)
      )

    return list(
      self._input_api.AffectedFiles(
        file_filter=file_filter, include_deletes=False
      )
    )

  @classmethod
  def changed_lines(cls, affected_file: AffectedFile) -> set[int]:
    return {lineno for lineno, _ in affected_file.ChangedContents()}

  def iter_python_files(self) -> Iterator[PythonFile]:
    for affected_file in self.affected_python_files():
      changed_lines: set[int] = self.changed_lines(affected_file)
      if not changed_lines:
        continue
      file_path: str = affected_file.LocalPath()
      full_path: pathlib.Path = self.root_path / file_path
      content: str = self._input_api.ReadFile(str(full_path), "r")
      yield PythonFile(
        file_path,
        content,
        changed_lines,
      )

  @classmethod
  def parse_bypass_reason(cls, description: str, key: str) -> str | None:
    pattern: str = rf"^[ \t]*{re.escape(key)}[ \t]*=[ \t]*(\S.*)$"
    for match in re.finditer(
      pattern, description, re.MULTILINE | re.IGNORECASE
    ):
      reason: str = match.group(1).strip()
      if reason.lower() not in PLACEHOLDER_BYPASS_REASONS:
        return reason
    return None

  def bypass_reason(self, key: str) -> str | None:
    return self.parse_bypass_reason(self.description, key)


class AstCheckVisitor(ast.NodeVisitor, metaclass=abc.ABCMeta):
  def __init__(self) -> None:
    super().__init__()
    self._violations: list[RawAstViolation] = []

  @property
  def violations(self) -> tuple[RawAstViolation, ...]:
    return tuple(self._violations)

  def add_violation(self, node: ast.stmt | ast.expr, name: str) -> None:
    self._violations.append(
      RawAstViolation(node.lineno, node.col_offset + 1, name)
    )

  @classmethod
  @abc.abstractmethod
  def report(
    cls,
    presubmit: PresubmitCheck,
    violations: Sequence[AstViolation],
  ) -> list[object]:
    raise NotImplementedError

  @classmethod
  def visit_source(cls, source: str) -> Sequence[RawAstViolation]:
    visitor = cls()
    visitor.visit(ast.parse(source))
    return visitor.violations

  @classmethod
  def visit_file(
    cls, input_api: InputApi, source: str
  ) -> Sequence[RawAstViolation]:
    # TODO(crbug.com/586521681): Remove workaround depot_tools is migrated to
    # 3.14.
    if sys.version_info >= (3, 14):  # noqa: UP036
      return cls.visit_source(source)
    out: str = subprocess.check_output(
      [
        input_api.python3_executable,
        "-c",
        f"import dataclasses, json, sys; "
        f"from {cls.__module__} import {cls.__name__}; "
        f"print(json.dumps([dataclasses.astuple(v) "
        f"for v in {cls.__name__}.visit_source(sys.stdin.read())]))",
      ],
      input=source,
      text=True,
      cwd=str(REPO_ROOT),
    )
    return [RawAstViolation(*v) for v in json.loads(out)]

  @classmethod
  def check(cls, input_api: InputApi, output_api: OutputApi) -> list[object]:
    return cls.check_all(input_api, output_api, (cls,))

  @classmethod
  def check_all(
    cls,
    input_api: InputApi,
    output_api: OutputApi,
    visitor_classes: Sequence[type[AstCheckVisitor]],
  ) -> list[object]:
    presubmit = PresubmitCheck(input_api, output_api)
    results: list[object] = []
    collected: dict[type[AstCheckVisitor], list[AstViolation]] = {
      v_cls: [] for v_cls in visitor_classes
    }
    for python_file in presubmit.iter_python_files():
      for v_cls in visitor_classes:
        violations = v_cls.visit_file(input_api, python_file.content)
        collected[v_cls].extend(AstViolation.from_raw(violations, python_file))
    for v_cls, violations in collected.items():
      results.extend(v_cls.report(presubmit, violations))
    return results
