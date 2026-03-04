# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import logging
import pathlib
import re
import unittest

import pytest
import tomllib
from tabulate import tabulate

import crossbench
from tests import test_helper

RUN_SNIPPET = """
if __name__ == "__main__":
  test_helper.run_pytest(__file__)
""".strip()
FUTURE_ANNOTATIONS_SNIPPET = "from __future__ import annotations"

COMMENTS_ONLY_RE = re.compile(r"^(?:#.*|\s*)*$", re.MULTILINE)

UNITTEST_DIR = pathlib.Path(__file__).parent
ROOT_DIR = UNITTEST_DIR.parents[1]
CROSSBENCH_DIR = ROOT_DIR / "crossbench"


class MetaTestCase(unittest.TestCase):

  def test_unittest_runner_snippet(self):
    # - All unittests files must end with the snippet for the CQ to pick it up.
    # - pytest files (in end2end) use a different approach that doesn't rely
    #   on a per-file runner
    for test_file in UNITTEST_DIR.glob("**/test_*.py"):
      with self.subTest(test_file=str(test_file)):
        self.assertTrue(
            test_file.read_text().rstrip().endswith(RUN_SNIPPET),
            f"{test_file} misses runner snippet: "
            "test_helper.run_pytest(__file__)")

  def test_future_annotation(self):
    for py_file in CROSSBENCH_DIR.glob("**/*.py"):
      with self.subTest(py_file=str(py_file)):
        text = py_file.read_text()
        if FUTURE_ANNOTATIONS_SNIPPET in text:
          continue
        if "pytype: skip-file" in text:
          continue
        if py_file.name == "__init__.py" and COMMENTS_ONLY_RE.fullmatch(text):
          continue
        self.fail(f"{py_file} is missing future annotation")

  def protobug_text_file_names(self):
    trace_config_dir = test_helper.config_dir()
    for config_file in trace_config_dir.glob("*.pbtxt"):
      self.fail(f"Invalid file extension, use .textpb: {config_file}")

  @pytest.mark.xfail
  def test_vpython_poetry_version_match(self):
    vpython_content = (ROOT_DIR / ".vpython3").read_text()
    poetry_lock_content = (ROOT_DIR / "poetry.lock").read_text()

    vpython_re = re.compile(
        r"name: \"infra/python/wheels/(?P<name>[^/\"]+).*?"
        r"version: \"version:(?P<version>[^\"]+)\"", re.DOTALL)
    poetry_re = re.compile(
        r'name = "(?P<name>[^"]+)".*?'
        r'version = "(?P<version>[^"]+)"', re.DOTALL)

    vpython_packages = {}
    for wheel_block in vpython_content.split("wheel: <"):
      if not wheel_block.strip():
        continue
      match = vpython_re.search(wheel_block)
      if match:
        name = match.group("name").split("-py")[0]
        version = match.group("version").split(".chromium")[0]
        vpython_packages[name] = version

    poetry_packages = {}
    for package_block in poetry_lock_content.split("[[package]]"):
      if not package_block.strip():
        continue
      match = poetry_re.search(package_block)
      if match:
        name = match.group("name")
        version = match.group("version")
        poetry_packages[name] = version

    self.assertGreater(
        len(vpython_packages), 0, "No packages found in .vpython3")
    self.assertGreater(
        len(poetry_packages), 0, "No packages found in poetry.lock")

    vpython_only = sorted(vpython_packages.keys() - poetry_packages.keys())
    if vpython_only:
      logging.warning("Packages only in .vpython3: %s", ", ".join(vpython_only))
    poetry_only = sorted(poetry_packages.keys() - vpython_packages.keys())
    if poetry_only:
      logging.warning("Packages only in poetry.lock: %s",
                      ", ".join(poetry_only))

    mismatches = []
    for name, vpython_version_str in vpython_packages.items():
      if name not in poetry_packages:
        continue
      poetry_version_str = poetry_packages[name]
      if vpython_version_str == poetry_version_str:
        continue
      mismatches.append((name, vpython_version_str, poetry_version_str))
    mismatches.sort(key=lambda row: row[0])
    if mismatches:
      headers = ["Package", ".vpython3", "poetry.lock"]
      self.fail("Version mismatches found:\n" +
                tabulate(mismatches, headers=headers))

  def test_dependencies_are_sorted(self):
    pyproject_toml_path = ROOT_DIR / "pyproject.toml"
    pyproject_toml = tomllib.loads(pyproject_toml_path.read_text())
    poetry_options = pyproject_toml["tool"]["poetry"]
    dependencies = poetry_options["dependencies"]
    sorted_dependencies = sorted(dependencies.keys())
    self.assertEqual(
        list(dependencies.keys()),
        sorted_dependencies,
        "Dependencies in pyproject.toml are not sorted alphabetically.",
    )
    dev_dependencies = poetry_options["group"]["dev"]["dependencies"]
    sorted_dev_dependencies = sorted(dev_dependencies.keys())
    self.assertEqual(
        list(dev_dependencies.keys()),
        sorted_dev_dependencies,
        "Dev dependencies in pyproject.toml are not sorted alphabetically.",
    )

  def test_version_match(self):
    pyproject_toml_path = ROOT_DIR / "pyproject.toml"
    pyproject_toml = tomllib.loads(pyproject_toml_path.read_text())
    pyproject_version = pyproject_toml["tool"]["poetry"]["version"]
    self.assertEqual(
        pyproject_version, crossbench.__version__,
        f"Version mismatch between {pyproject_toml_path} "
        "and crossbench.__version__")


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
