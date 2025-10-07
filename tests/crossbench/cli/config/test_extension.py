# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import pathlib

from crossbench.cli.config.extension import ExtensionConfig
from tests import test_helper
from tests.crossbench.cli.config.base import BaseConfigTestCase


class ExtensionConfigTestCase(BaseConfigTestCase):

  def test_crx(self):
    crx_file = pathlib.Path("/extension.crx")
    with self.assertRaisesRegex(argparse.ArgumentTypeError, "extension.crx"):
      ExtensionConfig.parse(crx_file)
    self.fs.create_file(crx_file, st_size=501)
    config = ExtensionConfig.parse(str(crx_file))
    self.assertEqual(config.crx, crx_file)
    self.assertEqual(config.id, None)
    self.assertEqual(config.unpacked, None)
    config_2 = ExtensionConfig.parse(crx_file)
    self.assertEqual(config, config_2)
    config_3 = ExtensionConfig.parse("extension.crx")
    self.assertEqual(config, config_3)

  def test_id(self):
    config = ExtensionConfig.parse("abcdefghijklmnopabcdefghijklmnop")
    self.assertEqual(config.crx, None)
    self.assertEqual(config.id, "abcdefghijklmnopabcdefghijklmnop")
    self.assertEqual(config.unpacked, None)

  def test_unpacked(self):
    manifest_file = pathlib.Path("/dir/manifest.json")
    self.fs.create_file(manifest_file, st_size=501)
    unpacked_dir = manifest_file.parent
    config = ExtensionConfig.parse(str(unpacked_dir))
    self.assertEqual(config.crx, None)
    self.assertEqual(config.id, None)
    self.assertEqual(config.unpacked, unpacked_dir)
    config = ExtensionConfig.parse(unpacked_dir)
    self.assertEqual(config.crx, None)
    self.assertEqual(config.id, None)
    self.assertEqual(config.unpacked, unpacked_dir)

  def test_does_not_exist(self):
    with self.assertRaises(argparse.ArgumentTypeError):
      ExtensionConfig.parse(str(pathlib.Path("does/not/exist")))
    with self.assertRaises(argparse.ArgumentTypeError):
      ExtensionConfig.parse(pathlib.Path("does/not/exist"))

  def test_exists_but_not_crx(self):
    cry_file = pathlib.Path("extension.cry")
    self.fs.create_file(cry_file, st_size=501)
    with self.assertRaises(argparse.ArgumentTypeError):
      ExtensionConfig.parse(str(cry_file))
    with self.assertRaises(argparse.ArgumentTypeError):
      ExtensionConfig.parse(cry_file)

  def test_unpacked_missing_manifest(self):
    unpacked_dir = pathlib.Path("dir")
    self.fs.create_dir(unpacked_dir)
    with self.assertRaises(argparse.ArgumentTypeError):
      ExtensionConfig.parse(str(unpacked_dir))
    with self.assertRaises(argparse.ArgumentTypeError):
      ExtensionConfig.parse(unpacked_dir)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
