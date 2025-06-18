# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import atexit
import contextlib
import logging
from typing import TYPE_CHECKING, Iterator, Self

from crossbench import exception

if TYPE_CHECKING:
  from crossbench.plt.base import Platform


class PortForwardException(Exception):
  pass


class PortScope:
  """ This class allows to forward ports in a local scope.
  The main PortManager is responsible for handling all forwarded ports, while
  the PortScope only tracks forwarded ports while it's active, and then tears
  down those forwarded ports when the scope is closed.
  """

  def __init__(self,
               manager: PortManager,
               parent_scope: Self | None = None) -> None:
    self._manager: PortManager = manager
    self._parent_scope: Self | None = parent_scope
    assert parent_scope is not self
    self.forwarded_ports: dict[int, int] = {}
    self.reverse_forwarded_ports: dict[int, int] = {}

  @property
  def platform(self) -> Platform:
    return self._manager.platform

  @property
  def is_nested(self) -> bool:
    return self._parent_scope is not None

  @property
  def is_empty(self) -> bool:
    return not self.forwarded_ports and not self.reverse_forwarded_ports

  @contextlib.contextmanager
  def nested(self) -> Iterator[PortScope]:
    with self._manager.nested() as scope:
      yield scope

  def is_forwarded_port_used(self, local_port: int) -> bool:
    return bool(self.lookup_forwarded_port(local_port))

  def is_reverse_forwarded_port_used(self, remote_port: int) -> bool:
    return bool(self.lookup_reverse_forwarded_port(remote_port))

  def lookup_forwarded_port(self, local_port: int) -> PortScope | None:
    for current_scope in self:
      if local_port in current_scope.forwarded_ports:
        return current_scope
    return None

  def lookup_reverse_forwarded_port(self, remote_port: int) -> PortScope | None:
    for current_scope in self:
      if remote_port in current_scope.reverse_forwarded_ports:
        return current_scope
    return None

  def __iter__(self) -> Iterator[Self]:
    current_scope: Self | None = self
    while current_scope:
      yield current_scope
      current_scope = current_scope._parent_scope

  def forward(self, local_port: int, remote_port: int) -> int:
    if self.is_forwarded_port_used(local_port):
      raise PortForwardException(
          f"Cannot forward local port {local_port} twice, "
          "it is already forwarded.")
    local_port = self.platform.port_forward(local_port, remote_port)
    self.forwarded_ports[local_port] = remote_port
    return local_port

  def stop_forward(self, local_port: int) -> None:
    if local_port not in self.forwarded_ports:
      raise PortForwardException(
          f"Cannot stop forwarding local port {local_port}, "
          f"it was never forwarded.")
    del self.forwarded_ports[local_port]
    self.platform.stop_port_forward(local_port)

  def reverse_forward(self, remote_port: int, local_port: int) -> int:
    if self.is_reverse_forwarded_port_used(remote_port):
      raise PortForwardException(
          f"Cannot reverse forward remote port {remote_port} twice, "
          "it is already forwarded.")
    remote_port = self.platform.reverse_port_forward(remote_port, local_port)
    self.reverse_forwarded_ports[remote_port] = local_port
    return remote_port

  def stop_reverse_forward(self, remote_port: int) -> None:
    if remote_port not in self.reverse_forwarded_ports:
      raise PortForwardException(
          f"Cannot stop reverse forwarding remote port {remote_port}, "
          f"it was never forwarded.")
    del self.reverse_forwarded_ports[remote_port]
    self.platform.stop_reverse_port_forward(remote_port)


class PortManager:
  """Keeps track of opened forwarded and reverse-forwarded ports.
  All ports are closed when the PortManager is closed.
  To limit the risk of leaking ports you can use the .nested() scope.

  Global PortManager (one instance per platform)
  - with PortScope 1:
    - forward port 1
    - forward port 2
    yield
    - disable port 1
    - disable port 2
  - with PortScope 2:
    ...

  """

  def __init__(self, platform: Platform, throw: bool = False) -> None:
    self._platform: Platform = platform
    self._throw: bool = throw
    self._is_active: bool = False
    # Keeps track of scoped ports.
    self._port_scope: PortScope = PortScope(self, None)
    self._start()

  def _start(self):
    assert not self._is_active, f"Cannot activate {self} twice"
    assert self._port_scope.is_empty, "Expected empty port scope"
    self._is_active = True
    atexit.register(self.stop)

  @property
  def scope(self) -> PortScope:
    return self._port_scope

  @property
  def platform(self) -> Platform:
    return self._platform

  @contextlib.contextmanager
  def nested(self) -> Iterator[PortScope]:
    """Open a nested port scope, all forwarded ports that were opened
    during this scope will be closed when leaving the scope. """
    old_scope = self._port_scope
    self._port_scope = PortScope(self, self._port_scope)
    try:
      yield self._port_scope
    finally:
      try:
        self._stop_current_scoped_ports()
      finally:
        self._port_scope = old_scope

  def assert_is_active(self):
    if not self._is_active:
      raise PortForwardException("Need active PortManager")

  @property
  def is_empty(self):
    return self._port_scope.is_empty and not self.has_nested_scopes

  @property
  def has_nested_scopes(self) -> bool:
    return self._port_scope.is_nested

  def stop(self) -> None:
    self.assert_is_active()
    atexit.unregister(self.stop)
    self._stop_all()
    self._is_active = False

  def _stop_all(self) -> None:
    if self.has_nested_scopes:
      logging.error("Closing PortManager with open nested port scopes")

    exceptions = exception.Annotator(self._throw)
    for port_scope in self._port_scope:
      with exceptions.capture("Stopping port forwarding"):
        self._stop_scoped_ports(port_scope, exceptions)
    exceptions.assert_success("Could not stop all port forwarding")

  def _stop_current_scoped_ports(self):
    exceptions = exception.Annotator(self._throw)
    self._stop_scoped_ports(self._port_scope, exceptions)
    exceptions.assert_success("Could not stop all port forwarding")

  def _stop_scoped_ports(self, port_scope: PortScope,
                         exceptions: exception.Annotator) -> None:
    for local_port in tuple(port_scope.forwarded_ports.keys()):
      with exceptions.capture(f"Stopping forwarding {local_port}"):
        port_scope.stop_forward(local_port)

    for remote_port in tuple(port_scope.reverse_forwarded_ports.keys()):
      with exceptions.capture(f"Stopping reverse forwarding {remote_port}"):
        port_scope.stop_reverse_forward(remote_port)

    assert self._port_scope.is_empty, "Expected empty PortScope"

  def forward(self, local_port: int, remote_port: int) -> int:
    return self._port_scope.forward(local_port, remote_port)

  def stop_forward(self, local_port: int) -> None:
    self._port_scope.stop_forward(local_port)

  def reverse_forward(self, remote_port: int, local_port: int) -> int:
    return self._port_scope.reverse_forward(remote_port, local_port)

  def stop_reverse_forward(self, remote_port: int) -> None:
    self._port_scope.stop_reverse_forward(remote_port)
