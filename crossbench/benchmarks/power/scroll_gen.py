# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import dataclasses
import enum
import math
import sys
from typing import ClassVar, Sequence


class ScrollDirection(enum.Enum):
  DOWN = enum.auto()
  UP = enum.auto()


SWIPE_DURATION_SEC = 0.75
SETTLE_DURATION_SEC = 0.15
LIFT_DURATION_SEC = 0.10
SWIPES_PER_DIRECTION = 5
SINGLE_CYCLE_DURATION = (
    SWIPE_DURATION_SEC + SETTLE_DURATION_SEC + LIFT_DURATION_SEC)
SINGLE_SEQUENCE_DURATION = 2 * SWIPES_PER_DIRECTION * SINGLE_CYCLE_DURATION


@dataclasses.dataclass(frozen=True)
class GeneratorConfig:
  frequency: int
  max_x: int
  max_y: int
  repetitions: int

  def y_top(self) -> int:
    return int(0.2 * self.max_y)

  def y_bottom(self) -> int:
    return int(0.8 * self.max_y)

  def fixed_x(self) -> int:
    return int(0.5 * self.max_x)


class EvemuEvent:
  """Helper to construct and print EVEMU event groups."""

  PRESSURE: ClassVar[int] = 50
  TOUCH_MAJOR: ClassVar[int] = 30

  EV_SYN: ClassVar[int] = 0x0000
  EV_KEY: ClassVar[int] = 0x0001
  EV_ABS: ClassVar[int] = 0x0003

  SYN_REPORT: ClassVar[int] = 0x0000
  BTN_TOUCH: ClassVar[int] = 0x014a

  ABS_MT_SLOT: ClassVar[int] = 0x002f
  ABS_MT_TOUCH_MAJOR: ClassVar[int] = 0x0030
  ABS_MT_POSITION_X: ClassVar[int] = 0x0035
  ABS_MT_POSITION_Y: ClassVar[int] = 0x0036
  ABS_MT_TRACKING_ID: ClassVar[int] = 0x0039
  ABS_MT_PRESSURE: ClassVar[int] = 0x003a

  def __init__(self, timestamp: float) -> None:
    self.time: float = timestamp
    self.events: list[tuple[int, int, int]] = []

  def _add(self, etype: int, code: int, value: int) -> None:
    self.events.append((etype, code, value))

  def set_btn_touch(self, value: int) -> None:
    self._add(self.EV_KEY, self.BTN_TOUCH, value)

  def set_tracking_id(self, value: int) -> None:
    self._add(self.EV_ABS, self.ABS_MT_TRACKING_ID, value)

  def set_x(self, value: int) -> None:
    self._add(self.EV_ABS, self.ABS_MT_POSITION_X, value)

  def set_y(self, value: int) -> None:
    self._add(self.EV_ABS, self.ABS_MT_POSITION_Y, value)

  def set_pressure(self, value: int) -> None:
    self._add(self.EV_ABS, self.ABS_MT_PRESSURE, value)

  def set_touch_major(self, value: int) -> None:
    self._add(self.EV_ABS, self.ABS_MT_TOUCH_MAJOR, value)

  def emit(self) -> None:
    """Outputs formatted event lines to stdout, followed by sync report."""
    for etype, code, value in self.events:
      print(f"E: {self.time:.6f} {etype:04x} {code:04x} {value:04d}")
    print(f"E: {self.time:.6f} {self.EV_SYN:04x} {self.SYN_REPORT:04x} 0000")


def parse_arguments(argv: Sequence[str]) -> GeneratorConfig:
  parser = argparse.ArgumentParser(description="EVEMU Swipe Generator")
  parser.add_argument(
      "--max_x", type=int, default=-1, help="The maximum of the X coordinate.")
  parser.add_argument(
      "--max_y", type=int, default=-1, help="The maximum of the Y coordinate.")
  parser.add_argument(
      "--rate", type=int, default=120, help="The refresh frequency.")
  parser.add_argument(
      "--repetitions",
      type=int,
      default=18,
      help="Number of scroll repetitions.")

  args = parser.parse_args(argv)

  frequency = args.rate
  assert frequency > 0, f"Frequency must be > 0, got {frequency}"

  max_x = args.max_x
  max_y = args.max_y
  assert max_x > 0, f"MAX_X must be > 0, got {max_x}"
  assert max_y > 0, f"MAX_Y must be > 0, got {max_y}"

  repetitions = args.repetitions
  assert repetitions > 0, f"Repetitions must be > 0, got {repetitions}"

  return GeneratorConfig(frequency, max_x, max_y, repetitions)


def print_header(config: GeneratorConfig) -> None:
  header = f"""# EVEMU 1.2
N: synaptics_tcm_touch
I: 0000 0000 0001 0001
P: 02 00 00 00 00 00 00 00
B: 00 0b 00 00 00 00 00 00 00
B: 01 00 00 00 00 00 00 00 00
B: 01 00 00 00 00 00 00 00 00
B: 01 00 80 00 00 00 00 00 00
B: 01 00 00 00 00 00 00 00 00
B: 01 00 00 00 00 00 00 00 00
B: 01 20 04 00 00 00 00 00 00
B: 01 00 00 00 00 00 00 00 00
B: 01 00 00 00 00 00 00 00 00
B: 01 00 00 00 00 00 00 00 00
B: 01 00 00 00 00 00 00 00 00
B: 01 00 00 00 00 00 00 00 00
B: 01 00 00 00 00 00 00 00 00
B: 02 00 00 00 00 00 00 00 00
B: 03 03 00 00 01 00 80 f3 06
B: 04 00 00 00 00 00 00 00 00
B: 05 00 00 00 00 00 00 00 00
B: 11 00 00 00 00 00 00 00 00
B: 12 00 00 00 00 00 00 00 00
A: 00 0 {config.max_x} 0 0 0
A: 01 0 {config.max_y} 0 0 0
A: 18 0 255 0 0 0
A: 2f 0 9 0 0 0
A: 30 0 {config.max_y} 0 0 0
A: 31 0 {config.max_x} 0 0 0
A: 34 -4096 4096 0 0 0
A: 35 0 {config.max_x} 0 0 0
A: 36 0 {config.max_y} 0 0 0
A: 37 0 2 0 0 0
A: 39 0 65535 0 0 0
A: 3a 0 255 0 0 0"""
  print(header)
  sys.stdout.flush()


def generate_event(time: float, x: int, y: int,
                   finger_down: bool) -> EvemuEvent:
  event = EvemuEvent(time)
  event.set_btn_touch(1 if finger_down else 0)
  event.set_tracking_id(0 if finger_down else -1)
  event.set_x(x)
  event.set_y(y)
  if finger_down:
    event.set_pressure(EvemuEvent.PRESSURE)
    event.set_touch_major(EvemuEvent.TOUCH_MAJOR)
  return event


def generate_swipes(time: float, direction: ScrollDirection,
                    config: GeneratorConfig) -> float:
  if direction is ScrollDirection.DOWN:
    start_y = config.y_bottom()
    end_y = config.y_top()
  else:
    start_y = config.y_top()
    end_y = config.y_bottom()

  period = 1.0 / config.frequency
  input_frames = int(SWIPE_DURATION_SEC * config.frequency)
  settle_frames = int(SETTLE_DURATION_SEC * config.frequency)

  for _ in range(SWIPES_PER_DIRECTION):
    cycle_start_time = time

    # 1. Touch down (1 frame)
    generate_event(time, config.fixed_x(), start_y, finger_down=True).emit()
    time += period

    # 2. Move (sinusoidal y-axis, no x-axis) (input_frames - 1)
    for i in range(1, input_frames):
      progress = i / input_frames
      # Sine easing: starts slow, peaks in middle, ends slow.
      multiplier = (1 - math.cos(math.pi * progress)) / 2
      current_y_pos = start_y + (end_y - start_y) * multiplier
      generate_event(
          time, config.fixed_x(), int(current_y_pos), finger_down=True).emit()
      time += period

    # Frames generated: 1 Touch Down Frame + (input_frames - 1) = input_frames
    # 3. Settle Time (Idle with finger on screen to prevent fling effect)
    for _ in range(settle_frames):
      generate_event(time, config.fixed_x(), end_y, finger_down=True).emit()
      time += period

    # 4. Lift finger (Idle with finger off screen)
    generate_event(time, config.fixed_x(), end_y, finger_down=False).emit()

    # 5. User's finger moves while NOT touching the screen,
    # reaching its new location, from which it will swipe again.
    time = cycle_start_time + SINGLE_CYCLE_DURATION

  return time


def main(argv: Sequence[str]) -> None:
  config = parse_arguments(argv)
  print_header(config)

  time = 0.0

  for _ in range(config.repetitions):
    time = generate_swipes(time, ScrollDirection.DOWN, config)
    time = generate_swipes(time, ScrollDirection.UP, config)


if __name__ == "__main__":
  main(sys.argv[1:])
