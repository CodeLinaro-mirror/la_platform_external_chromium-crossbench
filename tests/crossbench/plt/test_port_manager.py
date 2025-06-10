# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import unittest
from typing import Dict

from crossbench.plt.port_manager import PortForwardException
from tests import test_helper
from tests.crossbench.mock_helper import LinuxMockPlatform


class FakePortLinuxMockPlatform(LinuxMockPlatform):

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.forwarded_ports: Dict[int, int] = {}
    self.reverse_forwarded_ports: Dict[int, int] = {}
    self.current_port = 60000

  def _next_port(self) -> int:
    self.current_port += 1
    return self.current_port

  def port_forward(self, local_port: int, remote_port: int) -> int:
    if local_port == 0:
      local_port = self._next_port()
    self.forwarded_ports[local_port] = remote_port
    return local_port

  def stop_port_forward(self, local_port: int) -> None:
    if local_port in self.forwarded_ports:
      del self.forwarded_ports[local_port]

  def reverse_port_forward(self, remote_port: int, local_port: int) -> int:
    if remote_port == 0:
      remote_port = self._next_port()
    self.reverse_forwarded_ports[remote_port] = local_port
    return remote_port

  def stop_reverse_port_forward(self, remote_port: int) -> None:
    if remote_port in self.reverse_forwarded_ports:
      del self.reverse_forwarded_ports[remote_port]


class PortManagerTestCase(unittest.TestCase):

  def setUp(self):
    super().setUp()
    self.platform = FakePortLinuxMockPlatform()
    self.port_manager = self.platform.ports
    self.port_manager.assert_is_active()

  def tearDown(self):
    self.assertFalse(self.platform.forwarded_ports)
    self.assertFalse(self.platform.reverse_forwarded_ports)
    self.assertTrue(self.port_manager.is_empty)
    super().tearDown()

  def test_default(self):
    self.assertTrue(self.port_manager.is_empty)
    self.assertFalse(self.port_manager.has_nested_scopes)
    self.port_manager.assert_is_active()

  def test_nested(self):
    with self.port_manager.nested():
      self.assertFalse(self.port_manager.is_empty)
      self.assertTrue(self.port_manager.has_nested_scopes)
      self.port_manager.assert_is_active()

  def test_stop(self):
    self.port_manager.stop()
    self.assertTrue(self.port_manager.is_empty)
    self.assertFalse(self.port_manager.has_nested_scopes)

  def test_forward_port(self):
    with self.port_manager.nested() as port_scope:
      returned_local_port = port_scope.forward(12345, 8080)
      self.assertEqual(returned_local_port, 12345)
      self.assertIn(12345, self.platform.forwarded_ports)
      self.assertEqual(self.platform.forwarded_ports[12345], 8080)
      self.assertFalse(port_scope.is_empty)
    self.assertFalse(self.platform.forwarded_ports)
    self.assertTrue(port_scope.is_empty)

  def test_forward_port_auto_assign(self):
    with self.port_manager.nested() as port_scope:
      returned_local_port = port_scope.forward(0, 8080)
      self.assertEqual(returned_local_port, 60001)
      self.assertIn(60001, self.platform.forwarded_ports)

  def test_stop_forward_port(self):
    with self.port_manager.nested() as port_scope:
      port_scope.forward(12345, 8080)
      port_scope.stop_forward(12345)
      self.assertNotIn(12345, self.platform.forwarded_ports)

  def test_forward_port_conflict(self):
    with self.port_manager.nested() as port_scope:
      port_scope.forward(12345, 8080)
      with self.assertRaises(PortForwardException):
        # Try to forward same local port
        port_scope.forward(12345, 8081)

  def test_stop_forward_port_not_forwarded(self):
    with self.port_manager.nested() as port_scope:
      with self.assertRaises(PortForwardException):
        port_scope.stop_forward(12345)

  def test_reverse_forward_port(self):
    with self.port_manager.nested() as port_scope:
      returned_remote_port = port_scope.reverse_forward(54321, 8081)
      self.assertEqual(returned_remote_port, 54321)
      self.assertIn(54321, self.platform.reverse_forwarded_ports)
      self.assertEqual(self.platform.reverse_forwarded_ports[54321], 8081)
      self.assertFalse(port_scope.is_empty)

  def test_reverse_forward_port_auto_assign(self):
    with self.port_manager.nested() as port_scope:
      returned_remote_port = port_scope.reverse_forward(0, 8081)
      self.assertEqual(returned_remote_port, 60001)
      self.assertIn(60001, self.platform.reverse_forwarded_ports)

  def test_stop_reverse_forward_port(self):
    with self.port_manager.nested() as port_scope:
      port_scope.reverse_forward(54321, 8081)
      port_scope.stop_reverse_forward(54321)
      self.assertNotIn(54321, self.platform.reverse_forwarded_ports)

  def test_reverse_forward_port_conflict(self):
    with self.port_manager.nested() as port_scope:
      port_scope.reverse_forward(54321, 8081)
      with self.assertRaises(PortForwardException):
        # Try to reverse forward same remote port
        port_scope.reverse_forward(54321, 8082)

  def test_stop_reverse_forward_port_not_forwarded(self):
    with self.port_manager.nested() as port_scope:
      with self.assertRaises(PortForwardException):
        port_scope.stop_reverse_forward(54321)

  def test_nested_cleanup(self):
    self.port_manager.forward(1111, 2222)
    with self.port_manager.nested() as port_scope:
      port_scope.forward(3333, 4444)
    self.assertIn(1111, self.platform.forwarded_ports)
    self.assertNotIn(3333, self.platform.forwarded_ports)
    self.assertFalse(self.port_manager.has_nested_scopes)
    self.port_manager.stop()
    self.assertTrue(self.port_manager.is_empty)
    self.assertNotIn(1111, self.platform.forwarded_ports)
    self.assertNotIn(3333, self.platform.forwarded_ports)

  def test_forward_nested_cleanup_stop_outer(self):
    self.port_manager.forward(1111, 2222)
    with self.port_manager.nested() as port_scope:
      port_scope.forward(3333, 4444)
      port_scope.stop_forward(3333)
      with self.assertRaisesRegex(PortForwardException, "1111"):
        port_scope.stop_forward(1111)
    self.port_manager.stop_forward(1111)

  def test_reverse_forward_nested_cleanup_stop_outer(self):
    self.port_manager.reverse_forward(1111, 2222)
    with self.port_manager.nested() as port_scope:
      port_scope.reverse_forward(3333, 4444)
      port_scope.stop_reverse_forward(3333)
      with self.assertRaisesRegex(PortForwardException, "1111"):
        port_scope.stop_reverse_forward(1111)
    self.port_manager.stop_reverse_forward(1111)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
