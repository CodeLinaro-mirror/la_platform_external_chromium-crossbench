# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import unittest
from unittest import mock

import requests

from crossbench.pinpoint.api import PINPOINT_CONFIG_API_URL
from crossbench.pinpoint.list_bots import fetch_bots, print_bots
from tests import test_helper


class ListBotsTest(unittest.TestCase):

  def setUp(self):
    self.patcher_get_auth_session = mock.patch(
        "crossbench.pinpoint.list_bots.get_auth_session")
    self.mock_get_auth_session = self.patcher_get_auth_session.start()

    self.patcher_annotate = mock.patch("crossbench.pinpoint.list_bots.annotate")
    self.mock_annotate = self.patcher_annotate.start()

    self.mock_session = mock.Mock(spec=requests.Session)
    self.mock_get_auth_session.return_value = self.mock_session

    def mock_post_side_effect(url, *args, **kwargs):
      self.assertEqual(url, PINPOINT_CONFIG_API_URL,
                       f"Unexpected URL called: {url}")

      mock_response = mock.Mock()
      mock_response.json.return_value = {
          "configurations": ["bot1", "bot2", "bot3"]
      }
      mock_response.raise_for_status.return_value = None
      return mock_response

    self.mock_session.post.side_effect = mock_post_side_effect

  def tearDown(self):
    self.patcher_get_auth_session.stop()
    self.patcher_annotate.stop()

  def test_fetch_bots(self):
    bots = fetch_bots()

    self.assertEqual(bots, ["bot1", "bot2", "bot3"])
    self.mock_get_auth_session.assert_called_once()
    self.mock_session.post.assert_called_once_with(PINPOINT_CONFIG_API_URL)

  def test_fetch_bots_api_error(self):
    self.mock_session.post.side_effect = requests.exceptions.HTTPError(
        "API Error")

    with self.assertRaises(requests.exceptions.HTTPError):
      fetch_bots()

    self.mock_get_auth_session.assert_called_once()
    self.mock_session.post.assert_called_once_with(PINPOINT_CONFIG_API_URL)

  @mock.patch("builtins.print")
  def test_print_bots(self, mock_print):
    print_bots()
    mock_print.assert_called_once_with("bot1\nbot2\nbot3")


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
