# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import abc
import dataclasses
import datetime as dt
import subprocess
import time
from typing import TYPE_CHECKING, Final, Iterable

from immutabledict import immutabledict

from crossbench.action_runner.config import VirtualDeviceType
from crossbench.action_runner.input_events import InputEvent, KeyEvent, \
    WaitEvent
from crossbench.plt.base import Platform

if TYPE_CHECKING:
  from crossbench.action_runner.config import VirtualDeviceConfig
  from crossbench.plt.types import TupleCmdArgs

# Simplified mapping for common W3C to Linux EV_KEY codes
# See linux/input-event-codes.h
W3C_TO_LINUX: Final[immutabledict[str, int]] = immutabledict({
    "KeyA": 30,
    "KeyB": 48,
    "KeyC": 46,
    "KeyD": 32,
    "KeyE": 18,
    "KeyF": 33,
    "KeyG": 34,
    "KeyH": 35,
    "KeyI": 23,
    "KeyJ": 36,
    "KeyK": 37,
    "KeyL": 38,
    "KeyM": 50,
    "KeyN": 49,
    "KeyO": 24,
    "KeyP": 25,
    "KeyQ": 16,
    "KeyR": 19,
    "KeyS": 31,
    "KeyT": 20,
    "KeyU": 22,
    "KeyV": 47,
    "KeyW": 17,
    "KeyX": 45,
    "KeyY": 21,
    "KeyZ": 44,
    "Digit1": 2,
    "Digit2": 3,
    "Digit3": 4,
    "Digit4": 5,
    "Digit5": 6,
    "Digit6": 7,
    "Digit7": 8,
    "Digit8": 9,
    "Digit9": 10,
    "Digit0": 11,
    "Enter": 28,
    "Escape": 1,
    "Backspace": 14,
    "Tab": 15,
    "Space": 57,
    "Minus": 12,
    "Equal": 13,
    "BracketLeft": 26,
    "BracketRight": 27,
    "Backslash": 43,
    "Semicolon": 39,
    "Quote": 40,
    "Backquote": 41,
    "Comma": 51,
    "Period": 52,
    "Slash": 53,
    "ShiftLeft": 42,
    "ShiftRight": 54,
    "ControlLeft": 29,
    "ControlRight": 97,
    "AltLeft": 56,
    "AltRight": 100,
    "MetaLeft": 125,
    "MetaRight": 126,
})

EV_SYN: Final[int] = 0x0000
EV_KEY: Final[int] = 0x0001
SYN_REPORT: Final[int] = 0x0000

_EVEMU_KEYBOARD_HEADER: Final[bytes] = b"""# EVEMU 1.2
N: Virtual Keyboard (Crossbench)
I: 0003 18d2 2c42 0111
# Properties: none
P: 00 00 00 00 00 00 00 00
B: 00 0b 00 00 00 00 00 00 00
B: 01 fe ff ff ff ff ff 7f ff
B: 01 1f 00 c0 53 da bf 0e 31
B: 01 00 40 00 40 00 10 80 00
B: 01 00 00 00 00 13 00 00 01
B: 01 00 00 00 00 00 00 00 00
B: 01 00 00 00 00 00 00 10 00
B: 01 00 00 00 00 00 00 00 00
B: 01 00 00 01 00 00 00 00 00
B: 01 00 00 00 00 00 00 00 00
B: 01 80 04 20 00 00 00 00 00
B: 01 00 00 00 00 00 00 00 00
B: 01 00 00 00 00 00 00 00 00
B: 02 00 00 00 00 00 00 00 00
B: 03 00 00 00 00 00 00 00 00
B: 04 10 00 00 00 00 00 00 00
B: 05 00 00 00 00 00 00 00 00
B: 11 00 00 00 00 00 00 00 00
B: 12 00 00 00 00 00 00 00 00
"""


# Buffer added to timestamps on consecutive injections to ensure events arrive
# on the device ahead of their target playback time, preventing uinput/evemu
# from discarding inter-event delays in "catch-up" mode due to transport latency
# or clock drift.
_INPUT_LEAD_BUFFER: Final[dt.timedelta] = dt.timedelta(milliseconds=50)
# Buffer added to the sleep duration after injection to allow the virtual
# device process and OS input pipeline to fully drain and dispatch queued
# events before Crossbench proceeds.
_INPUT_DRAIN_BUFFER: Final[dt.timedelta] = dt.timedelta(milliseconds=50)


@dataclasses.dataclass
class VirtualDeviceState:
  proc: subprocess.Popen
  start_time: dt.timedelta | None = None


class EvemuPlatformMixin(Platform, metaclass=abc.ABCMeta):
  """
  Mixin for Platforms that support executing standard
  Linux (evemu) strings.
  """

  def __init__(self, *args, **kwargs) -> None:
    super().__init__(*args, **kwargs)
    self._virtual_devices: dict[str, VirtualDeviceState] = {}

  @abc.abstractmethod
  def _get_evemu_device_cmd(self,
                            device_type: VirtualDeviceType) -> TupleCmdArgs:
    pass

  def setup_virtual_devices(
      self, virtual_devices: tuple[VirtualDeviceConfig, ...]) -> None:
    for device_config in virtual_devices:
      if device_config.device_type == VirtualDeviceType.KEYBOARD:
        self._init_virtual_keyboard(device_config.name)
      else:
        raise ValueError(
            f"Unsupported virtual device type: {device_config.device_type}")

  def _init_virtual_keyboard(self, device_name: str) -> None:
    state = self._virtual_devices.get(device_name)
    if state is None or state.proc.poll() is not None:
      cmd = self._get_evemu_device_cmd(VirtualDeviceType.KEYBOARD)
      proc = self.popen(*cmd, stdin=subprocess.PIPE)
      assert proc.stdin is not None
      proc.stdin.write(_EVEMU_KEYBOARD_HEADER)
      proc.stdin.flush()
      self._virtual_devices[device_name] = VirtualDeviceState(proc)

  def _execute_evemu_script(self, device_name: str, script: str) -> None:
    state = self._virtual_devices.get(device_name)
    if state is None:
      raise RuntimeError(f"Virtual device '{device_name}' was not initialized. "
                         "Call setup_virtual_devices() first.")
    assert state.proc.stdin is not None
    state.proc.stdin.write(script.encode("utf-8"))
    state.proc.stdin.flush()

  def inject_input_events(self, device_name: str,
                          events: Iterable[InputEvent]) -> None:
    """Injects abstract input events by translating them into an evemu script.

    Blocks until all events are processed. Applies a lead buffer on consecutive
    injections so events arrive ahead of their target timestamps and a drain
    buffer to ensure all dispatched events finish processing.
    """
    state = self._virtual_devices.get(device_name)
    if state is None:
      raise RuntimeError(f"Virtual device '{device_name}' was not initialized. "
                         "Call setup_virtual_devices() first.")
    now = dt.timedelta(seconds=time.monotonic())
    if state.start_time is None:
      state.start_time = now
      start_time = dt.timedelta()
      lead_buffer = dt.timedelta()
    else:
      # Pad consecutive injections with a lead buffer so timestamps are in the
      # future relative to the device playback clock, preventing catch-up mode.
      lead_buffer = _INPUT_LEAD_BUFFER
      start_time = (now - state.start_time) + lead_buffer

    script, end_time = self._generate_evemu_events_string(events, start_time)

    if not script:
      return

    duration = end_time - start_time
    self._execute_evemu_script(device_name, script)
    # Block for the playback duration plus lead and drain buffers so the host
    # waits until the device completes event playback and pipeline dispatch.
    if duration or lead_buffer:
      self.sleep(duration + lead_buffer + _INPUT_DRAIN_BUFFER)

  def _generate_evemu_events_string(
      self,
      events: Iterable[InputEvent],
      start_time: dt.timedelta = dt.timedelta(),
  ) -> tuple[str, dt.timedelta]:
    lines: list[str] = []
    current_time = start_time

    for event in events:
      if isinstance(event, WaitEvent):
        current_time += event.duration
      elif isinstance(event, KeyEvent):
        linux_code = W3C_TO_LINUX.get(event.key_code)
        if linux_code is None:
          raise ValueError(f"W3C key code '{event.key_code}' is not supported.")

        value = 1 if event.is_down else 0

        sec = int(current_time.total_seconds())
        usec = current_time.microseconds
        timestamp = f"{sec}.{usec:06d}"

        lines.append(
            f"E: {timestamp} {EV_KEY:04x} {linux_code:04x} {value:04d}")
        lines.append(f"E: {timestamp} {EV_SYN:04x} {SYN_REPORT:04x} 0000")
      else:
        raise ValueError(f"Unsupported event type: {type(event).__name__}")

    return ("\n".join(lines) + "\n" if lines else ""), current_time
