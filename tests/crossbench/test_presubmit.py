# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import ast
import unittest
from unittest import mock

from tests import test_helper
from tools.presubmit import banned_builtins


class BannedBuiltinVisitorTestCase(unittest.TestCase):

  def _check(self, code: str) -> list[tuple[int, int, str]]:
    tree = ast.parse(code)
    visitor = banned_builtins.BannedBuiltinVisitor()
    visitor.visit(tree)
    return visitor.violations

  def test_getattr_detection(self) -> None:
    self.assertEqual(
        self._check("getattr(obj, 'prop')"),
        [(1, 1, "getattr")],
    )
    self.assertEqual(
        self._check("getattr(obj, 'prop', default)"),
        [(1, 1, "getattr")],
    )
    self.assertEqual(
        self._check("builtins.getattr(obj, 'prop')"),
        [(1, 1, "getattr")],
    )

  def test_setattr_detection(self) -> None:
    self.assertEqual(
        self._check("setattr(obj, 'prop', 123)"),
        [(1, 1, "setattr")],
    )
    self.assertEqual(
        self._check("builtins.setattr(obj, 'prop', 123)"),
        [(1, 1, "setattr")],
    )

  def test_hasattr_detection(self) -> None:
    self.assertEqual(
        self._check("hasattr(obj, 'prop')"),
        [(1, 1, "hasattr")],
    )
    self.assertEqual(
        self._check("builtins.hasattr(obj, 'prop')"),
        [(1, 1, "hasattr")],
    )

  def test_allowed_calls(self) -> None:
    self.assertEqual(self._check("obj.prop"), [])
    self.assertEqual(self._check("obj.getattr('prop')"), [])
    self.assertEqual(self._check("obj.setattr('prop', 1)"), [])
    self.assertEqual(self._check("obj.hasattr('prop')"), [])


class MockAffectedFile:

  def __init__(self, path: str, changed_lines: set[int] | None = None) -> None:
    self._path = path
    self._changed_lines = changed_lines

  def LocalPath(self) -> str:  # noqa: N802
    return self._path

  def ChangedContents(self) -> list[tuple[int, str]]:  # noqa: N802
    if self._changed_lines is None:
      return [(i, "") for i in range(1, 1000)]
    return [(lineno, "") for lineno in self._changed_lines]


class CheckNoBannedBuiltinsTestCase(unittest.TestCase):

  def _mock_input_api(
      self,
      files: dict[str, str],
      changed_lines_map: dict[str, set[int]] | None = None,
      description: str = "",
  ) -> mock.MagicMock:
    input_api = mock.MagicMock()
    input_api.PresubmitLocalPath.return_value = "/root"
    input_api.fnmatch.fnmatch.return_value = False
    input_api.os_path.exists.side_effect = lambda path: str(path).replace(
        "/root/", "") in files
    input_api.ReadFile.side_effect = lambda path, mode="r": files[str(
        path).replace("/root/", "")]
    input_api.change.DescriptionText.return_value = description
    input_api.change.FullDescriptionText.return_value = description

    affected_files = []
    for file_path in files:
      changed_lines = (
          changed_lines_map.get(file_path) if changed_lines_map else None)
      affected_files.append(MockAffectedFile(file_path, changed_lines))

    input_api.AffectedFiles.side_effect = (
        lambda file_filter=None, include_deletes=True:
        [f for f in affected_files if (file_filter is None or file_filter(f))])
    return input_api

  def _mock_output_api(self) -> mock.MagicMock:
    output_api = mock.MagicMock()
    output_api.PresubmitError.side_effect = lambda msg, items=(
    ), long_text="": (
        "ERROR",
        msg,
        items,
        long_text,
    )
    output_api.PresubmitNotifyResult.side_effect = lambda msg: ("NOTIFY", msg)
    return output_api

  def test_no_violations(self) -> None:
    input_api = self._mock_input_api({"foo.py": "x = obj.field\n"})
    output_api = self._mock_output_api()
    results = banned_builtins.CheckNoBannedBuiltins(input_api, output_api)
    self.assertEqual(results, [])

  def test_getattr_error_on_new_code(self) -> None:
    input_api = self._mock_input_api(
        {"foo.py": "x = getattr(obj, 'field', None)\n"},
        description="Fix something",
    )
    output_api = self._mock_output_api()
    results = banned_builtins.CheckNoBannedBuiltins(input_api, output_api)
    self.assertEqual(len(results), 1)
    status, msg, items, long_text = results[0]
    self.assertEqual(status, "ERROR")
    self.assertIn("Found banned built-in function calls", msg)
    self.assertEqual(len(items), 1)
    self.assertIn("foo.py:1:5: x = getattr(obj, 'field', None)", items[0])
    self.assertIn("ALLOW_GETATTR=<REASON>", long_text)

  def test_getattr_ignored_on_unchanged_line(self) -> None:
    content = (
        "# Line 1\n"
        "x = getattr(obj, 'field', None)\n"  # Line 2 (not in changed lines)
        "# Line 3\n"
        "y = obj.other_field\n"  # Line 4 (in changed lines)
    )
    input_api = self._mock_input_api(
        {"foo.py": content},
        changed_lines_map={"foo.py": {4}},
        description="Fix something",
    )
    output_api = self._mock_output_api()
    results = banned_builtins.CheckNoBannedBuiltins(input_api, output_api)
    self.assertEqual(results, [])

  def test_getattr_passed_with_bypass(self) -> None:
    input_api = self._mock_input_api(
        {"foo.py": "x = getattr(obj, 'field', None)\n"},
        description="Fix something\n\nALLOW_GETATTR=Need dynamic field lookup",
    )
    output_api = self._mock_output_api()
    results = banned_builtins.CheckNoBannedBuiltins(input_api, output_api)
    self.assertEqual(len(results), 1)
    status, msg = results[0]
    self.assertEqual(status, "NOTIFY")
    self.assertIn("Bypassing banned built-in check", msg)
    self.assertIn("ALLOW_GETATTR=Need dynamic field lookup", msg)

  def test_hasattr_error_on_new_code(self) -> None:
    input_api = self._mock_input_api(
        {"foo.py": "if hasattr(obj, 'field'): pass\n"},
        description="Fix something",
    )
    output_api = self._mock_output_api()
    results = banned_builtins.CheckNoBannedBuiltins(input_api, output_api)
    self.assertEqual(len(results), 1)
    status, msg, items, long_text = results[0]
    self.assertEqual(status, "ERROR")
    self.assertIn("Found banned built-in function calls", msg)
    self.assertEqual(len(items), 1)
    self.assertIn("foo.py:1:4: if hasattr(obj, 'field'): pass", items[0])
    self.assertIn("ALLOW_HASATTR=<REASON>", long_text)

  def test_hasattr_passed_with_bypass(self) -> None:
    input_api = self._mock_input_api(
        {"foo.py": "if hasattr(obj, 'field'): pass\n"},
        description="Fix something\n\nALLOW_HASATTR=Need dynamic check",
    )
    output_api = self._mock_output_api()
    results = banned_builtins.CheckNoBannedBuiltins(input_api, output_api)
    self.assertEqual(len(results), 1)
    status, msg = results[0]
    self.assertEqual(status, "NOTIFY")
    self.assertIn("Bypassing banned built-in check", msg)
    self.assertIn("ALLOW_HASATTR=Need dynamic check", msg)

  def test_both_bypass_required(self) -> None:
    input_api = self._mock_input_api(
        {
            "foo.py": ("x = getattr(obj, 'field', None)\n"
                       "setattr(obj, 'field', 123)\n")
        },
        description=("Fix something\n\n"
                     "ALLOW_GETATTR=Need dynamic lookup\n"
                     "ALLOW_SETATTR=Need dynamic setter"),
    )
    output_api = self._mock_output_api()
    results = banned_builtins.CheckNoBannedBuiltins(input_api, output_api)
    self.assertEqual(len(results), 1)
    status, msg = results[0]
    self.assertEqual(status, "NOTIFY")
    self.assertIn("Bypassing banned built-in check", msg)
    self.assertIn("ALLOW_GETATTR=Need dynamic lookup", msg)
    self.assertIn("ALLOW_SETATTR=Need dynamic setter", msg)

  def test_partial_bypass_fails(self) -> None:
    input_api = self._mock_input_api(
        {
            "foo.py": ("x = getattr(obj, 'field', None)\n"
                       "setattr(obj, 'field', 123)\n")
        },
        description="Fix something\n\nALLOW_GETATTR=Dynamic lookup",
    )
    output_api = self._mock_output_api()
    results = banned_builtins.CheckNoBannedBuiltins(input_api, output_api)
    self.assertEqual(len(results), 1)
    status, _, items, long_text = results[0]
    self.assertEqual(status, "ERROR")
    self.assertEqual(len(items), 2)
    self.assertIn("ALLOW_SETATTR=<REASON>", long_text)

  def test_placeholder_bypass_rejected(self) -> None:
    input_api = self._mock_input_api(
        {"foo.py": "x = getattr(obj, 'field', None)\n"},
        description="Fix something\n\nALLOW_GETATTR=TODO",
    )
    output_api = self._mock_output_api()
    results = banned_builtins.CheckNoBannedBuiltins(input_api, output_api)
    self.assertEqual(len(results), 1)
    status, _, _, _ = results[0]
    self.assertEqual(status, "ERROR")


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
