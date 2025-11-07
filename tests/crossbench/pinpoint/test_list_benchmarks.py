# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import unittest
from unittest import mock

import requests

from crossbench.exception import MultiException
from crossbench.pinpoint.api import CHROMEPERF_TEST_SUITES_API_URL
from crossbench.pinpoint.list_benchmarks import fetch_benchmarks, \
    print_benchmarks
from tests import test_helper


class ListBenchmarksTest(unittest.TestCase):

  def setUp(self):
    self.patcher_get_auth_session = mock.patch(
        "crossbench.pinpoint.list_benchmarks.get_auth_session")
    self.mock_get_auth_session = self.patcher_get_auth_session.start()

    self.mock_session = mock.Mock(spec=requests.Session)
    self.mock_get_auth_session.return_value = self.mock_session

    def mock_post_side_effect(url, *args, **kwargs):
      self.assertEqual(url, CHROMEPERF_TEST_SUITES_API_URL,
                       f"Unexpected URL called: {url}")

      mock_response = mock.Mock()
      mock_response.json.return_value = [
          "benchmark1", "benchmark2", "benchmark3"
      ]
      mock_response.raise_for_status.return_value = None
      return mock_response

    self.mock_session.post.side_effect = mock_post_side_effect

  def tearDown(self):
    self.patcher_get_auth_session.stop()

  def test_fetch_benchmarks(self):
    benchmarks = fetch_benchmarks()

    self.assertEqual(benchmarks, ["benchmark1", "benchmark2", "benchmark3"])
    self.mock_get_auth_session.assert_called_once()
    self.mock_session.post.assert_called_once_with(
        CHROMEPERF_TEST_SUITES_API_URL)

  def test_fetch_benchmarks_api_error(self):
    self.mock_session.post.side_effect = requests.exceptions.HTTPError(
        "API Error")

    with self.assertRaises(MultiException):
      fetch_benchmarks()

    self.mock_get_auth_session.assert_called_once()
    self.mock_session.post.assert_called_once_with(
        CHROMEPERF_TEST_SUITES_API_URL)

  @mock.patch("builtins.print")
  def test_print_benchmarks(self, mock_print):
    print_benchmarks()
    mock_print.assert_called_with("benchmark1\nbenchmark2\nbenchmark3")


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
