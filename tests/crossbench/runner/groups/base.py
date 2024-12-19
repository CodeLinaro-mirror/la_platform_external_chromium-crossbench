# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file

from typing import Optional

from crossbench.browsers.browser import Browser
from crossbench.flags.base import Flags
from crossbench.runner.groups.session import BrowserSessionRunGroup
from tests.crossbench.runner.helper import BaseRunnerTestCase


class BaseRunGroupTestCase(BaseRunnerTestCase):

  def setUp(self):
    super().setUp()
    self.root_dir = self.out_dir / "custom"
    self.runner = self.default_runner()

  def default_session(self,
                      browser: Optional[Browser] = None,
                      throw: bool = True):
    browser = browser or self.browsers[0]
    return BrowserSessionRunGroup(self.runner.env, self.runner.probes, browser,
                                  Flags(), 0, self.root_dir,
                                  self.runner.create_symlinks, throw)
