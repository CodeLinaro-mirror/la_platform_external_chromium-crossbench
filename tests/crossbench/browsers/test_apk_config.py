# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
from crossbench.browsers.apk_config import ApkConfig
from tests import test_helper
from tests.crossbench.base import CrossbenchFakeFsTestCase


class ApkConfigTestCase(CrossbenchFakeFsTestCase):

  def test_parse_str_apk(self) -> None:
    created_path = self.create_file("/tmp/app.apk", contents="data")
    config = ApkConfig.parse(str(created_path))
    self.assertTrue(config.path.exists())
    self.assertEqual(config.path.name, "app.apk")

  def test_parse_invalid_extension(self) -> None:
    self.create_file("/tmp/app.zip", contents="data")
    with self.assertRaises(argparse.ArgumentTypeError):
      ApkConfig.parse("/tmp/app.zip")

  def test_parse_dict(self) -> None:
    created_path = self.create_file("/tmp/app.apk", contents="data")
    config = ApkConfig.parse({
        "path": str(created_path),
        "reinstall": False,
        "modules": "base",
    })
    self.assertTrue(config.path.exists())
    self.assertEqual(config.path.name, "app.apk")
    self.assertFalse(config.reinstall)
    self.assertEqual(config.modules, "base")


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
