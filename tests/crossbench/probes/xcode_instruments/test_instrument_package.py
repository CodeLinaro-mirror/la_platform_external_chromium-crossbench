# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import contextlib
import plistlib
import unittest
from typing import Final, Iterator
from unittest import mock

from crossbench import path as pth
from crossbench.plt.bin import Binaries
from crossbench.probes.profiling.context.macos import MAC_INSTRUMENT_PATH
from crossbench.probes.xcode_instruments.instrument_package import (
  InstrumentPackage,
)
from tests import test_helper
from tests.crossbench.base import CrossbenchFakeFsTestCase

_SOURCE: Final[str] = """<?xml version="1.0" encoding="UTF-8" ?>
<package>
  <id>org.example</id>
  <title>Package Title</title>
  <owner><name>Owner</name></owner>
  <instrument>
    <id>org.example.counters</id>
    <title> Counters </title>
  </instrument>
  <instrument>
    <id>org.example.signposts</id>
    <title>Signposts</title>
  </instrument>
</package>
"""

_XCODE_CONTENTS: Final[str] = "/Applications/Xcode.app/Contents"
_APPLE_PACKAGES: Final[str] = (
  f"{_XCODE_CONTENTS}/Applications/Instruments.app/Contents/Packages"
)
_CACHE_DIR: Final[str] = "/tmp/cache/instrument_packages"


class InstrumentPackageTestCase(CrossbenchFakeFsTestCase):
  def setUp(self) -> None:
    super().setUp()
    self.source = pth.LocalPath("/tmp/example.instrpkg")
    self.fs.create_file(self.source, contents=_SOURCE)

  def test_parse_instrument_titles(self):
    self.assertEqual(
      InstrumentPackage.parse_instrument_titles(self.source),
      ("Counters", "Signposts"),
    )

  def test_parse_instrument_titles_none(self):
    self.fs.create_file(
      "/tmp/empty.instrpkg", contents="<package><id>org.x</id></package>"
    )
    with self.assertRaisesRegex(ValueError, "No instruments"):
      InstrumentPackage.parse_instrument_titles(
        pth.LocalPath("/tmp/empty.instrpkg")
      )

  def test_parse_source(self):
    self.assertEqual(
      InstrumentPackage.parse_source(str(self.source)), self.source
    )

  def test_parse_source_invalid(self):
    self.fs.create_file("/tmp/broken.instrpkg", contents="<package>")
    self.fs.create_file("/tmp/empty.instrpkg", contents="<package/>")
    for value in (
      "/tmp/broken.instrpkg",
      "/tmp/empty.instrpkg",
      "/tmp/missing.instrpkg",
    ):
      with self.subTest(value=value):
        with self.assertRaises(argparse.ArgumentTypeError):
          InstrumentPackage.parse_source(value)

  def test_record_args(self):
    package = InstrumentPackage(
      pth.LocalPath("/tmp/example.instrdst"), ("Counters", "Signposts")
    )
    self.assertEqual(
      package.record_args,
      (
        "--package",
        pth.LocalPath("/tmp/example.instrdst"),
        "--instrument",
        "Counters",
        "--instrument",
        "Signposts",
      ),
    )

  def _mock_host(self) -> mock.Mock:
    self.fs.create_file(
      f"{_XCODE_CONTENTS}/version.plist",
      contents=plistlib.dumps(
        {
          "ProductBuildVersion": "27A266a",
        }
      ).decode(),
    )
    self.fs.create_dir(_CACHE_DIR)
    apple_packages = pth.LocalPath(_APPLE_PACKAGES)
    host = mock.Mock()
    host.sh_stdout.return_value = f"{_XCODE_CONTENTS}/Developer\n"
    host.local_cache_dir.return_value = pth.LocalPath(_CACHE_DIR)
    host.exists.side_effect = lambda path: pth.LocalPath(path).exists()
    host.read_bytes.side_effect = lambda path: pth.LocalPath(path).read_bytes()
    host.glob.return_value = [
      apple_packages / "CPU Profiler.instrdst",
      apple_packages / "CPU Counters.instrdst",
    ]

    def fake_build(*args) -> None:
      self.fs.create_dir(args[args.index("-o") + 1])

    host.sh.side_effect = fake_build
    host.rename.side_effect = lambda src, dst: pth.LocalPath(src).rename(dst)
    return host

  @contextlib.contextmanager
  def _mock_binaries(self) -> Iterator[None]:
    with (
      mock.patch.object(
        Binaries.XCRUN,
        "resolve_cached",
        return_value=pth.LocalPath("/usr/bin/xcrun"),
      ),
      mock.patch.object(
        Binaries.XCODE_SELECT,
        "resolve_cached",
        return_value=pth.LocalPath("/usr/bin/xcode-select"),
      ),
    ):
      yield

  def test_build_links_all_apple_packages(self):
    host = self._mock_host()
    with self._mock_binaries():
      package = InstrumentPackage.build(host, self.source)
    self.assertEqual(package.instruments, ("Counters", "Signposts"))
    self.assertEqual(package.path.parent, pth.LocalPath(_CACHE_DIR))
    self.assertRegex(
      package.path.name, r"^example-27A266a-[0-9a-f]{16}\.instrdst$"
    )
    self.assertTrue(package.path.is_dir())
    host.sh_stdout.assert_called_once_with(
      pth.LocalPath("/usr/bin/xcode-select"), "-p"
    )
    host.glob.assert_called_once_with(
      pth.LocalPath(_APPLE_PACKAGES), "*.instrdst"
    )
    host.sh.assert_called_once_with(
      pth.LocalPath("/usr/bin/xcrun"),
      "instrumentbuilder",
      "-i",
      self.source,
      "-o",
      package.path.with_name(f"tmp-{package.path.name}"),
      "-L",
      pth.LocalPath(_APPLE_PACKAGES),
      "-l",
      "CPU Counters",
      "-l",
      "CPU Profiler",
    )

  def test_build_reuses_cached_package(self):
    host = self._mock_host()
    with self._mock_binaries():
      first = InstrumentPackage.build(host, self.source)
      second = InstrumentPackage.build(host, self.source)
    self.assertEqual(first, second)
    host.sh.assert_called_once()

  def test_build_rebuilds_changed_source(self):
    host = self._mock_host()
    with self._mock_binaries():
      first = InstrumentPackage.build(host, self.source)
      self.source.write_text(_SOURCE.replace("Signposts", "Points"))
      second = InstrumentPackage.build(host, self.source)
    self.assertNotEqual(first.path, second.path)
    self.assertEqual(second.instruments, ("Counters", "Points"))
    self.assertEqual(host.sh.call_count, 2)


class ShippedInstrumentPackagesTestCase(unittest.TestCase):
  def test_shipped_packages_declare_instruments(self):
    for source in (
      MAC_INSTRUMENT_PATH,
      test_helper.config_dir() / "doc/probe/xcode_instruments.example.instrpkg",
    ):
      with self.subTest(source=source.name):
        self.assertTrue(InstrumentPackage.parse_instrument_titles(source))


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
