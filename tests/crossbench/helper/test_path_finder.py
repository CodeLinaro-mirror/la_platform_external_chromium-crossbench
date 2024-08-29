# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import pathlib
from unittest import mock

from crossbench.helper.path_finder import (ChromiumBuildBinaryFinder,
                                           ChromiumCheckoutFinder,
                                           V8CheckoutFinder, V8ToolsFinder)
from tests import test_helper
from tests.crossbench.base import BaseCrossbenchTestCase
from tests.crossbench.mock_helper import (LinuxMockPlatform, MacOsMockPlatform,
                                          WinMockPlatform)


class BaseCheckoutTestCase(BaseCrossbenchTestCase):

  def _add_v8_checkout_files(self, checkout_dir: pathlib.Path) -> None:
    self.assertIsNone(V8CheckoutFinder(self.platform).path)
    (checkout_dir / ".git").mkdir(parents=True)
    self.assertIsNone(V8CheckoutFinder(self.platform).path)
    self.fs.create_file(checkout_dir / "include" / "v8.h", st_size=100)

  def _add_chrome_checkout_files(self, checkout_dir: pathlib.Path) -> None:
    self.assertIsNone(ChromiumCheckoutFinder(self.platform).path)
    self._add_v8_checkout_files(checkout_dir / "v8")
    (checkout_dir / ".git").mkdir(parents=True)
    self.assertIsNone(ChromiumCheckoutFinder(self.platform).path)
    (checkout_dir / "chrome").mkdir(parents=True)


class V8CheckoutFinderTestCase(BaseCheckoutTestCase):

  def test_find_none(self):
    self.assertIsNone(V8CheckoutFinder(self.platform).path)

  def test_D8_PATH(self):
    with mock.patch.dict(os.environ, {}, clear=True):
      self.assertIsNone(V8CheckoutFinder(self.platform).path)
    candidate_dir = pathlib.Path("/custom/v8/")
    d8_path = candidate_dir / "out/x64.release/d8"
    with mock.patch.dict(os.environ, {"D8_PATH": str(d8_path)}, clear=True):
      self.assertIsNone(V8CheckoutFinder(self.platform).path)
    self._add_v8_checkout_files(candidate_dir)
    with mock.patch.dict(os.environ, {"D8_PATH": str(d8_path)}, clear=True):
      self.assertEqual(V8CheckoutFinder(self.platform).path, candidate_dir)
    # Still NONE without custom D8_PATH env var.
    self.assertIsNone(V8CheckoutFinder(self.platform).path)

  def test_known_location(self):
    checkout_dir = pathlib.Path.home() / "v8/v8"
    self.assertIsNone(V8CheckoutFinder(self.platform).path)
    checkout_dir.mkdir(parents=True)
    self._add_v8_checkout_files(checkout_dir)
    self.assertEqual(V8CheckoutFinder(self.platform).path, checkout_dir)

  def test_module_relative(self):
    with mock.patch.dict(os.environ, {}, clear=True):
      self.assertIsNone(V8CheckoutFinder(self.platform).path)
      path = pathlib.Path(__file__)
      self.assertFalse(path.exists())
      if "google3" in path.parts:
        fake_chrome_root = path.parents[6]
      else:
        # In:   chromium/src/third_party/crossbench/tests/crossbench/probes/test_helper.py
        # Out:  chromium/src
        fake_chrome_root = path.parents[5]
      checkout_dir = fake_chrome_root / "v8"
      self.assertIsNone(V8CheckoutFinder(self.platform).path)
      self._add_chrome_checkout_files(fake_chrome_root)
      self.assertIsNotNone(ChromiumCheckoutFinder(self.platform).path)
      self.assertEqual(V8CheckoutFinder(self.platform).path, checkout_dir)


class ChromiumBuildBinaryFinderTestCase(BaseCheckoutTestCase):

  def test_find_none(self):
    finder = ChromiumBuildBinaryFinder(self.platform, "custom_binary")
    self.assertIsNone(finder.path)
    self.assertIsNone(finder.path)
    self.assertEqual(finder.binary_name, "custom_binary")
    candidate_dir = pathlib.Path("/chr/src/out/x64.Release")
    self.assertIsNone(
        ChromiumBuildBinaryFinder(self.platform, "custom_binary",
                                  (candidate_dir,)).path)

  def test_find_candidate(self):
    checkout_dir = pathlib.Path("/foo/bar/chr/src/")
    candidate = checkout_dir / "out/x64.Release/custom_binary"
    self.fs.create_file(candidate, st_size=100)
    self.assertTrue(candidate.is_file)
    self.assertIsNone(
        ChromiumBuildBinaryFinder(self.platform, "custom_binary",
                                  (candidate.parent,)).path)
    self._add_chrome_checkout_files(checkout_dir)
    self.assertEqual(
        ChromiumBuildBinaryFinder(self.platform, "custom_binary",
                                  (candidate.parent,)).path, candidate)

  def test_find_default(self):
    checkout_dir = pathlib.Path.home() / "Documents/chromium/src"
    candidate = checkout_dir / "out/Release/custom_binary"
    self.fs.create_file(candidate, st_size=100)
    assert checkout_dir.is_dir()
    self._add_chrome_checkout_files(checkout_dir)
    self.assertEqual(
        ChromiumBuildBinaryFinder(self.platform, "custom_binary").path,
        candidate)


class V8ToolsFinderTestCase(BaseCheckoutTestCase):

  def test_defaults(self):
    # TODO: use AndroidAdbMockPlatform(self.platform) as well
    for platform in (self.platform, LinuxMockPlatform(), MacOsMockPlatform(),
                     WinMockPlatform()):
      finder = V8ToolsFinder(platform)
      self.assertIsNone(finder.d8_binary)
      self.assertIsNone(finder.v8_checkout)
      self.assertIsNone(finder.tick_processor)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
