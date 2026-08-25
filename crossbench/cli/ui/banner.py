# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import colorsys
import logging
import random
from typing import TYPE_CHECKING, Sequence

from crossbench import plt
from crossbench.cli.ui import ui

if TYPE_CHECKING:
  from crossbench.benchmarks.base import Benchmark
  from crossbench.cli.config.browser_variants import BrowserVariantConfig
  from crossbench.cli.subcommand.benchmark import BenchmarkSubcommand

BANNER = r"""
                   ▌           ▌    │  Browser Benchmark Runner
    ▞▀▖▙▀▖▞▀▖▞▀▘▞▀▘▛▀▖▞▀▖▛▀▖▞▀▖▛▀▖  │  v{version}
    ▌ ▖▌  ▌ ▌▝▀▖▝▀▖▌ ▌▛▀ ▌ ▌▌ ▖▌ ▌  │  {extra_info}
    ▝▀ ▘  ▝▀ ▀▀ ▀▀ ▀▀ ▝▀▘▘ ▘▝▀ ▘ ▘  │  {browser_info}
"""


class Banner:

  @classmethod
  def print(cls, subcommand: BenchmarkSubcommand, benchmark: Benchmark,
            variants: Sequence[BrowserVariantConfig]) -> None:
    version_str = cls._get_version_info()
    extra_info = cls.benchmark_banner_info(subcommand)
    browser_info = cls.browser_banner_info(variants)

    if subcommand.cli.args.verbosity < 0:
      cls._log_version_info(version_str)
    else:
      cls._print_banner_logo(version_str, extra_info, browser_info)

    cls.log_stories(benchmark)
    cls.log_variants(variants)

  @classmethod
  def benchmark_banner_info(cls, subcommand: BenchmarkSubcommand) -> str:
    benchmark_name = subcommand.benchmark_name()
    version_str = subcommand.benchmark_version()
    return f"{benchmark_name} {version_str}".strip()

  @classmethod
  def browser_banner_info(cls, variants: Sequence[BrowserVariantConfig]) -> str:
    if not variants:
      return ""

    if len(variants) == 1:
      variant = variants[0]
      return f"{variant.browser_cls.type_name()} {variant.platform.name}"

    if len(variants) < 4:
      return ", ".join(v.browser_cls.type_name() for v in variants)

    return f"{len(variants)} browsers"

  @classmethod
  def _get_version_info(cls) -> str:
    details = plt.PLATFORM.crossbench_details()
    version = details["version"]
    if current_hash := details.get("current_hash"):
      dirty = " (dirty)" if details.get("has_uncommitted_changes") else ""
      return f"{version} {current_hash[:12]}{dirty}"
    return version

  @classmethod
  def _log_version_info(cls, version: str) -> None:
    logging.info("🛠 v%s", version)

  @classmethod
  def _print_banner_logo(cls,
                         version: str,
                         extra_info: str | None = None,
                         browser_info: str | None = None) -> None:
    formatted_banner = BANNER.format(
        version=version,
        extra_info=extra_info or "",
        browser_info=browser_info or "")
    lines = formatted_banner.strip("\n").split("\n")

    if not ui.COLOR_LOGGING:
      print(formatted_banner.strip("\n"))
      return

    max_y = len(lines)
    max_x = max(len(line_len) for line_len in lines) if lines else 1
    start_hue = random.random()  # noqa: S311

    for y, line in enumerate(lines):
      colored_line = ""
      for x, char in enumerate(line):
        if char.isspace():
          colored_line += char
        else:
          nx = x / max_x
          ny = y / max_y
          hue = (start_hue + nx * 0.15 + ny * 0.1) % 1.0
          r, g, b = colorsys.hsv_to_rgb(hue, 0.5, 0.9)
          ir = int(r * 255)
          ig = int(g * 255)
          ib = int(b * 255)
          colored_line += f"\033[38;2;{ir};{ig};{ib}m{char}\033[0m"
      print(colored_line)

  @classmethod
  def log_stories(cls, benchmark: Benchmark) -> None:
    substory_names = [
        name for story in benchmark.stories for name in story.substories
    ]
    stories_str = ", ".join(substory_names)
    logging.info("📚 SELECTED %s STORIES AND %s SUBSTORIES: %s",
                 len(benchmark.stories), len(substory_names), stories_str)

  @classmethod
  def log_variants(cls, variants: Sequence[BrowserVariantConfig]) -> None:
    for variant in variants:
      logging.info("🌐 SELECTED BROWSER: name=%s path='%s' ", variant.label,
                   variant.path)
