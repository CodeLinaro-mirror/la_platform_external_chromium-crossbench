# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from __future__ import annotations

import os
import pathlib
import sys
from unittest import mock

from typing_extensions import override

from crossbench.helper.path_finder import ChromiumBuildBinaryFinder, \
    ChromiumCheckoutFinder, TraceboxFinder, TraceconvFinder, \
    TraceProcessorFinder, V8CheckoutFinder, V8ToolsFinder, WprGoFinder
from tests import test_helper
from tests.crossbench.base import BaseCrossbenchTestCase
from tests.crossbench.mock_helper import AndroidAdbMockPlatform, \
    LinuxMockPlatform, MacOsMockPlatform, MockAdb, WinMockPlatform
from tests.crossbench.plt.helper import BasePosixMockPlatformTestCase


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
    self.assertIsNone(V8CheckoutFinder(self.platform).local_path)

  def test_d8_path(self):
    with mock.patch.dict(os.environ, {}, clear=True):
      self.assertIsNone(V8CheckoutFinder(self.platform).path)
    candidate_dir = pathlib.Path("/custom/v8/")
    d8_path = candidate_dir / "out/x64.release/d8"
    with mock.patch.dict(os.environ, {"D8_PATH": str(d8_path)}, clear=True):
      self.assertIsNone(V8CheckoutFinder(self.platform).path)
    self._add_v8_checkout_files(candidate_dir)
    with mock.patch.dict(os.environ, {"D8_PATH": str(d8_path)}, clear=True):
      self.assertEqual(
          pathlib.Path(V8CheckoutFinder(self.platform).path), candidate_dir)
      self.assertEqual(
          V8CheckoutFinder(self.platform).local_path, candidate_dir)
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
      # In:   chromium/src/third_party/crossbench/tests/crossbench/probes/test_helper.py
      # Out:  chromium/src
      fake_chrome_root = path.parents[5]
      checkout_dir = fake_chrome_root / "v8"
      self.assertIsNone(V8CheckoutFinder(self.platform).path)
      self._add_chrome_checkout_files(fake_chrome_root)
      self.assertIsNotNone(ChromiumCheckoutFinder(self.platform).path)
      self.assertEqual(
          pathlib.Path(V8CheckoutFinder(self.platform).path), checkout_dir)


class ChromiumBuildBinaryFinderTestCase(BaseCheckoutTestCase):

  def test_find_none(self):
    finder = ChromiumBuildBinaryFinder(self.platform, "custom_binary", ())
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
        ChromiumBuildBinaryFinder(self.platform, "custom_binary", ()).path,
        candidate)

  def test_find_build_dir_from_candite(self):
    checkout_dir = pathlib.Path.home() / "Documents/some_chr/src"
    candidate = checkout_dir / "out/Release/custom_binary"
    self.fs.create_file(candidate, st_size=100)
    assert checkout_dir.is_dir()
    self._add_chrome_checkout_files(checkout_dir)
    self.assertIsNone(
        ChromiumBuildBinaryFinder(self.platform, "custom_binary", ()).path,)
    self.assertEqual(
        ChromiumBuildBinaryFinder(self.platform, "custom_binary",
                                  (checkout_dir / "out",)).path, candidate)
    self.assertEqual(
        ChromiumBuildBinaryFinder(self.platform, "custom_binary",
                                  (candidate.parent,)).path, candidate)


class PerfettoToolFinderTestCase(BaseCheckoutTestCase):

  def test_find_traceconv(self):
    self._find_tool(TraceconvFinder, "traceconv")

  def test_find_tracebox(self):
    self._find_tool(TraceboxFinder, "tracebox")

  def test_find_trace_processor(self):
    self._find_tool(TraceProcessorFinder, "trace_processor")

  def _find_tool(self, finder_cls, name):
    finder = finder_cls(self.platform)
    self.assertIsNone(finder.path)
    self.assertIsNone(finder.path)
    checkout_dir = pathlib.Path.home() / "Documents/chromium/src"
    false_candidate = checkout_dir / "third_party/perfetto/tools/another_binary"
    self.fs.create_file(false_candidate, st_size=100)
    self.assertIsNone(finder_cls(self.platform).path)
    candidate = checkout_dir / "third_party/perfetto/tools" / name
    self.fs.create_file(candidate, st_size=100)
    self.assertIsNone(finder_cls(self.platform).path)
    self._add_chrome_checkout_files(checkout_dir)
    self.assertEqual(finder_cls(self.platform).path, candidate)


class V8ToolsFinderTestCase(BaseCheckoutTestCase):

  def test_defaults(self):
    # TODO: use AndroidAdbMockPlatform(self.platform) as well
    for platform in (self.platform, LinuxMockPlatform(), MacOsMockPlatform(),
                     WinMockPlatform()):
      finder = V8ToolsFinder(platform)
      self.assertIsNone(finder.d8_binary)
      self.assertIsNone(finder.v8_checkout)
      self.assertIsNone(finder.tick_processor)
      self.assertIsNone(finder.v8_logviewer)

  def test_find_v8_tools(self):
    checkout_dir = pathlib.Path.home() / "v8/v8"
    self._add_v8_checkout_files(checkout_dir)

    tick_processor_name = "tools/linux-tick-processor"
    if self.platform.is_macos:
      tick_processor_name = "tools/mac-tick-processor"
    elif self.platform.is_win:
      tick_processor_name = "tools/windows-tick-processor.bat"

    self.fs.create_file(checkout_dir / tick_processor_name, st_size=100)
    self.fs.create_file(checkout_dir / "tools/v8-logviewer", st_size=100)

    d8_binary = checkout_dir / "out/Release/d8"
    self.fs.create_file(d8_binary, st_size=100)

    finder = V8ToolsFinder(
        self.platform, d8_binary=d8_binary, v8_checkout=checkout_dir)
    self.assertEqual(finder.d8_binary, d8_binary)
    self.assertEqual(finder.v8_checkout, checkout_dir)
    self.assertEqual(finder.tick_processor, checkout_dir / tick_processor_name)
    self.assertEqual(finder.v8_logviewer, checkout_dir / "tools/v8-logviewer")


class WprToolsFinderTestCase(BasePosixMockPlatformTestCase):

  __test__ = True

  @override
  def setup_host_platform(self) -> LinuxMockPlatform:
    return LinuxMockPlatform()

  @override
  def test_is_linux(self):
    self.assertTrue(self.platform.is_linux)

  def _with_arch(self, platform, arch):
    platform.machine = arch
    platform.use_mock_name = False
    return platform

  def _setup_adb(self):
    self.fs.create_file("/usr/bin/adb", contents="adb")
    self.platform.expect_sh(
        "/usr/bin/adb",
        "devices",
        "-l",
        result="List of devices attached\n123 device usb:0 product:a model:b")

  def test_httparchive_and_wpr_bins(self):
    self._with_arch(self.platform, "x64")
    self._setup_adb()
    android_platform = self._with_arch(
        AndroidAdbMockPlatform(self.platform, adb=MockAdb(self.platform)),
        "arm64")
    self.assertIsNone(WprGoFinder(self.platform).local_path)
    with self.assertRaises(FileNotFoundError):
      WprGoFinder(self.platform).httparchive()
    with self.assertRaises(FileNotFoundError):
      WprGoFinder(self.platform).wpr(android_platform)

    root = test_helper.root_dir()
    self.fs.create_dir(root / "third_party/webpagereplay")
    self.assertIsNone(WprGoFinder(self.platform).local_path)
    with self.assertRaises(FileNotFoundError):
      WprGoFinder(self.platform).httparchive()
    with self.assertRaises(FileNotFoundError):
      WprGoFinder(self.platform).wpr(android_platform)

    self.fs.create_file(root / "third_party/webpagereplay/scripts/build.py")
    self.assertIsNotNone(WprGoFinder(self.platform).local_path)
    self.platform.expect_sh(
        sys.executable,
        root / "third_party/webpagereplay/scripts/build.py",
        "--os",
        "linux",
        "--arch",
        "x64",
        "--out-dir",
        root / "cache/webpagereplay/linux/x64",
        "--binary",
        "httparchive",
        result="",
    )
    self.assertEqual(
        WprGoFinder(self.platform).httparchive(),
        root / "cache/webpagereplay/linux/x64/httparchive")

    self.platform.expect_sh(
        sys.executable,
        root / "third_party/webpagereplay/scripts/build.py",
        "--os",
        "android",
        "--arch",
        "arm64",
        "--out-dir",
        root / "cache/webpagereplay/android/arm64",
        "--binary",
        "wpr",
        result="",
    )
    self.assertEqual(
        WprGoFinder(self.platform).wpr(android_platform),
        root / "cache/webpagereplay/android/arm64/wpr")

  def test_httparchive_and_wpr_bins_with_overrides(self):
    self._with_arch(self.platform, "x64")
    self._setup_adb()
    android_platform = self._with_arch(
        AndroidAdbMockPlatform(self.platform, adb=MockAdb(self.platform)),
        "arm64")

    root = test_helper.root_dir()
    override_dir = root / "custom_wpr"
    self.fs.create_file(override_dir / "deterministic.js")
    self.fs.create_file(override_dir / "my_wpr")
    self.fs.create_file(override_dir / "my_httparchive")

    self.platform.set_binary_lookup_override("wpr", override_dir / "my_wpr")
    self.platform.set_binary_lookup_override("httparchive",
                                             override_dir / "my_httparchive")

    finder = WprGoFinder(self.platform)
    self.assertEqual(finder.local_path, override_dir)
    self.assertEqual(finder.wpr(android_platform), override_dir / "my_wpr")
    self.assertEqual(finder.httparchive(), override_dir / "my_httparchive")


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
