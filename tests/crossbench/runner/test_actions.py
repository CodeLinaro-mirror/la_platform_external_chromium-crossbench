# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import contextlib
from typing import Iterator
from unittest import mock

from crossbench.action_runner.action.enums import WindowTarget
from crossbench.runner.actions import Actions
from tests import test_helper
from tests.crossbench.runner.groups.base import BaseRunGroupTestCase


class ActionsTestCase(BaseRunGroupTestCase):

  @contextlib.contextmanager
  def mock_js(self, actions: Actions) -> Iterator[mock.MagicMock]:
    with mock.patch.object(actions, "js") as mock_js:
      yield mock_js

  @contextlib.contextmanager
  def mock_show_url(self, actions: Actions) -> Iterator[mock.MagicMock]:
    with mock.patch.object(actions._browser, "show_url") as mock_show_url:
      yield mock_show_url

  def test_show_url_target_window_target_js(self):
    run = self.mock_run()
    with Actions("test", run) as actions:
      with self.mock_js(actions) as mock_js:
        actions.show_url("http://google.com", target=WindowTarget.BLANK)
        mock_js.assert_called_once_with(
            "window.open('http://google.com','_blank');")

  def test_show_url_target_window_target_browser(self):
    run = self.mock_run()
    with Actions("test", run) as actions:
      with self.mock_show_url(actions) as mock_show_url:
        actions.show_url("http://google.com", target=WindowTarget.NEW_TAB)
        mock_show_url.assert_called_once_with(
            "http://google.com", target=WindowTarget.NEW_TAB)

  def test_show_url_target_default(self):
    run = self.mock_run()
    with Actions("test", run) as actions:
      with self.mock_show_url(actions) as mock_show_url:
        actions.show_url("http://google.com")
        mock_show_url.assert_called_once_with(
            "http://google.com", target=WindowTarget.SELF)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
