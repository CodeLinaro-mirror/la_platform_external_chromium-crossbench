# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from tests.crossbench.base import CrossbenchFakeFsTestCase


class ActionRunnerTestCase(CrossbenchFakeFsTestCase):

  def tearDown(self):
    expected_sh_cmds = self.platform.expected_sh_cmds
    if expected_sh_cmds is not None:
      self.assertListEqual(expected_sh_cmds, [],
                           "Got additional unused shell cmds.")

    expected_js = self.browser.expected_js
    if expected_js is not None:
      self.assertListEqual(expected_js, [],
                           "Got additional unused expected JS.")
