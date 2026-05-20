# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import io
import logging
import unittest
from unittest import mock

from crossbench.cli.cli import CrossBenchCLI
from tests import test_helper


class CliLoggingTestCase(unittest.TestCase):

  def setUp(self):
    super().setUp()
    self.cli = CrossBenchCLI()

  def test_silenced_logging_success(self):
    # Initialize logging on original sys.stderr
    self.cli._init_logging()
    self.cli._setup_logging()

    with self.cli.silenced_logging():
      # Inside the silenced context, logging should go to redirected stream
      logging.info("This is a silenced log")

    # Restore and tear down logging
    self.cli._teardown_logging()

  def test_silenced_logging_exception(self):
    self.cli._init_logging()
    self.cli._setup_logging()

    fake_stderr = io.StringIO()
    with mock.patch("sys.stderr", fake_stderr):
      with self.assertRaises(ValueError):
        with self.cli.silenced_logging():
          logging.info("Error log message")
          raise ValueError("Test error")

      # The error log message should have been written to the fake_stderr
      self.assertIn("Error log message", fake_stderr.getvalue())

    self.cli._teardown_logging()


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
