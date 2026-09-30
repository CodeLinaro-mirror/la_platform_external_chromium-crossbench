# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import unittest
from unittest import mock

from crossbench.helper import input_helper
from crossbench.runner.pause_controller import PauseController, ResumeMode
from tests import test_helper


class PauseControllerTestCase(unittest.TestCase):

  def setUp(self) -> None:
    super().setUp()
    self.controller = PauseController(pause_on_error=True)

  def test_request_pause(self) -> None:
    self.assertFalse(self.controller.is_pause_requested)
    self.controller.request_pause()
    self.assertTrue(self.controller.is_pause_requested)

  def test_context_manager_registers_and_unregisters_ctrl_p(self) -> None:
    with mock.patch.object(
        input_helper.shared(), "register_key") as mock_register, \
         mock.patch.object(
             input_helper.shared(), "unregister_key") as mock_unregister:
      with self.controller:
        mock_register.assert_called_once_with("\x10",
                                              self.controller.request_pause)
        mock_unregister.assert_not_called()
      mock_unregister.assert_called_once_with("\x10")

  def test_check_pause_skips_when_not_requested_and_successful(self) -> None:
    with mock.patch.object(input_helper, "prompt") as mock_prompt:
      self.assertEqual(
          self.controller.check_pause(is_success=True), ResumeMode.CONTINUE)
      mock_prompt.assert_not_called()

  def test_check_pause_skips_on_error_when_pause_on_error_disabled(
      self) -> None:
    controller = PauseController(pause_on_error=False)
    with mock.patch.object(input_helper, "prompt") as mock_prompt:
      self.assertEqual(
          controller.check_pause(is_success=False), ResumeMode.CONTINUE)
      mock_prompt.assert_not_called()

  def test_check_pause_stop_choice_on_error(self) -> None:
    with mock.patch.object(input_helper, "prompt", return_value="s"):
      mode = self.controller.check_pause(is_success=False)
      self.assertEqual(mode, ResumeMode.STOP)

  def test_check_pause_continue_choice_when_requested(self) -> None:
    self.controller.request_pause()
    with mock.patch.object(input_helper, "prompt", return_value="c"):
      mode = self.controller.check_pause(is_success=True)
      self.assertEqual(mode, ResumeMode.CONTINUE)
    self.assertFalse(self.controller.is_pause_requested)

  def test_check_pause_empty_then_valid_choice(self) -> None:
    self.controller.request_pause()
    with mock.patch.object(
        input_helper, "prompt", side_effect=["", "c"]) as mock_prompt, \
         self.assertLogs(level="WARNING") as cm:
      mode = self.controller.check_pause(is_success=True)
    self.assertEqual(mode, ResumeMode.CONTINUE)
    self.assertEqual(mock_prompt.call_count, 2)
    output = "\n".join(cm.output)
    self.assertIn("Unknown action", output)

  def test_check_pause_invalid_then_valid_choice(self) -> None:
    self.controller.request_pause()
    with mock.patch.object(
        input_helper, "prompt", side_effect=["invalid", "s"]) as mock_prompt, \
         self.assertLogs(level="WARNING") as cm:
      mode = self.controller.check_pause(is_success=True)
    self.assertEqual(mode, ResumeMode.STOP)
    self.assertEqual(mock_prompt.call_count, 2)
    output = "\n".join(cm.output)
    self.assertIn("Unknown action", output)

  def test_check_pause_eof_stops(self) -> None:
    self.controller.request_pause()
    with mock.patch.object(
        input_helper, "prompt", side_effect=EOFError) as mock_prompt:
      mode = self.controller.check_pause(is_success=True)
    self.assertEqual(mode, ResumeMode.STOP)
    mock_prompt.assert_called_once()


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
