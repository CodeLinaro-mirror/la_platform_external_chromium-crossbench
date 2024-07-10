# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import enum
import unittest

from crossbench.helper.state import (BaseState, StateMachine,
                                     UnexpectedStateError)
from tests import test_helper


@enum.unique
class TestState(BaseState):
  INITIAL = enum.auto()
  READY = enum.auto()
  DONE = enum.auto()


class StateMachineTestCase(unittest.TestCase):

  def test_init(self):
    state_machine = StateMachine(TestState.INITIAL)
    self.assertIs(state_machine.state, TestState.INITIAL)
    state_machine = StateMachine(TestState.READY)
    self.assertIs(state_machine.state, TestState.READY)

  def test_eq(self):
    state_machine = StateMachine(TestState.READY)
    state_machine_2 = StateMachine(TestState.READY)
    self.assertEqual(state_machine, state_machine)
    self.assertEqual(state_machine, state_machine_2)
    self.assertEqual(state_machine, TestState.READY)
    self.assertNotEqual(state_machine, None)
    self.assertNotEqual(state_machine, TestState.INITIAL)
    self.assertNotEqual(state_machine, StateMachine(TestState.INITIAL))

  def test_transition(self):
    state_machine = StateMachine(TestState.INITIAL)
    state_machine.transition(TestState.INITIAL, to=TestState.READY)
    self.assertEqual(state_machine.state, TestState.READY)
    with self.assertRaises(UnexpectedStateError) as cm:
      state_machine.transition(TestState.INITIAL, to=TestState.READY)
    self.assertIn("INITIAL", str(cm.exception))
    self.assertIn("READY", str(cm.exception))

  def test_transition_multi_current(self):
    state_machine = StateMachine(TestState.INITIAL)
    state_machine.transition(
        TestState.INITIAL, TestState.READY, to=TestState.READY)
    self.assertEqual(state_machine.state, TestState.READY)
    state_machine.transition(
        TestState.INITIAL, TestState.READY, to=TestState.READY)
    self.assertEqual(state_machine.state, TestState.READY)
    state_machine.transition(
        TestState.INITIAL, TestState.READY, to=TestState.DONE)
    self.assertEqual(state_machine.state, TestState.DONE)
    with self.assertRaises(UnexpectedStateError) as cm:
      state_machine.transition(
          TestState.INITIAL, TestState.READY, to=TestState.DONE)
    self.assertIn("INITIAL", str(cm.exception))
    self.assertIn("READY", str(cm.exception))
    self.assertIn("DONE", str(cm.exception))

  def test_expect(self):
    state_machine = StateMachine(TestState.INITIAL)
    state_machine.expect(TestState.INITIAL)
    with self.assertRaises(RuntimeError) as cm:
      state_machine.expect(TestState.READY)
    self.assertIn("INITIAL", str(cm.exception))
    self.assertIn("READY", str(cm.exception))

  def test_expect_before(self):
    state_machine = StateMachine(TestState.INITIAL)
    state_machine.expect_before(TestState.READY)
    state_machine.expect_before(TestState.DONE)

    state_machine.transition(TestState.INITIAL, to=TestState.READY)
    with self.assertRaises(UnexpectedStateError) as cm:
      state_machine.expect_before(TestState.READY)
    self.assertEqual(cm.exception.state, TestState.READY)
    self.assertEqual(cm.exception.expected, (TestState.INITIAL,))
    state_machine.expect_before(TestState.DONE)

    state_machine.transition(TestState.READY, to=TestState.DONE)
    with self.assertRaises(UnexpectedStateError) as cm:
      state_machine.expect_before(TestState.DONE)
    self.assertEqual(cm.exception.state, TestState.DONE)
    self.assertEqual(cm.exception.expected,
                     (TestState.INITIAL, TestState.READY))

  def test_expect_at_least(self):
    state_machine = StateMachine(TestState.INITIAL)
    with self.assertRaises(UnexpectedStateError) as cm:
      state_machine.expect_at_least(TestState.READY)
    self.assertEqual(cm.exception.state, TestState.INITIAL)
    self.assertEqual(cm.exception.expected, (TestState.READY, TestState.DONE))
    with self.assertRaises(UnexpectedStateError) as cm:
      state_machine.expect_at_least(TestState.DONE)
    self.assertEqual(cm.exception.state, TestState.INITIAL)
    self.assertEqual(cm.exception.expected, (TestState.DONE,))

    state_machine.transition(TestState.INITIAL, to=TestState.READY)
    state_machine.expect_at_least(TestState.INITIAL)
    state_machine.expect_at_least(TestState.READY)
    with self.assertRaises(UnexpectedStateError) as cm:
      state_machine.expect_at_least(TestState.DONE)
    self.assertEqual(cm.exception.state, TestState.READY)
    self.assertEqual(cm.exception.expected, (TestState.DONE,))

    state_machine.transition(TestState.READY, to=TestState.DONE)
    state_machine.expect_at_least(TestState.INITIAL)
    state_machine.expect_at_least(TestState.READY)
    state_machine.expect_at_least(TestState.DONE)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
