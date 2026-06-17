# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import unittest
from typing import TYPE_CHECKING, ClassVar
from unittest import mock

from typing_extensions import override

from crossbench import path as pth
from crossbench.benchmarks.web_power.base import WebPowerBenchmarkBase, \
    WebPowerStory, _value_or
from crossbench.cli.config.network import NetworkConfig, NetworkType
from crossbench.cli.parser import CBArgumentParser
from crossbench.probes.bits import BitsProbe
from tests import test_helper
from tests.crossbench.benchmarks.helper import BaseBenchmarkTestCase

if TYPE_CHECKING:
  from crossbench.runner.run import Run


class MockWebPowerStory(WebPowerStory):

  @property
  @override
  def story_name(self) -> str:
    return "mock-story"

  def run(self, run: Run) -> None:
    pass


class MockWebPowerBenchmark(WebPowerBenchmarkBase):
  """Mock WebPowerBenchmark for testing."""

  DEFAULT_STORY_CLS: ClassVar = MockWebPowerStory


class ValueOrTestCase(unittest.TestCase):

  def test_value_or_with_value(self) -> None:
    self.assertEqual(_value_or(10, 5), 10)
    self.assertEqual(_value_or(0, 5), 0)
    self.assertEqual(_value_or("test", "default"), "test")
    self.assertEqual(_value_or(False, True), False)

  def test_value_or_with_none(self) -> None:
    self.assertEqual(_value_or(None, 5), 5)
    self.assertEqual(_value_or(None, "default"), "default")


class WebPowerStoryTestCase(unittest.TestCase):

  def test_from_site(self) -> None:
    youtube_story = MockWebPowerStory.from_site(
        "youtube", total_duration=dt.timedelta(seconds=123))
    self.assertEqual(youtube_story.url,
                     "https://www.youtube.com/watch?v=XITHbsUUlYI")
    self.assertEqual(youtube_story.name, "web-power-mock-story-youtube")
    self.assertEqual(youtube_story.duration, dt.timedelta(seconds=123))

    cnn_story = MockWebPowerStory.from_site(
        "cnn", total_duration=dt.timedelta(seconds=123))
    self.assertEqual(cnn_story.url, "https://www.cnn.com")
    self.assertEqual(cnn_story.name, "web-power-mock-story-cnn")
    self.assertEqual(cnn_story.duration, dt.timedelta(seconds=123))

  def test_from_invalid_site(self) -> None:
    with self.assertRaisesRegex(ValueError,
                                "Unknown web power benchmark site key"):
      MockWebPowerStory.from_site(
          "invalid-site", total_duration=dt.timedelta(seconds=123))

  def test_from_url(self) -> None:
    story = MockWebPowerStory.from_url(
        "https://www.google.com", total_duration=dt.timedelta(seconds=123))
    self.assertEqual(story.url, "https://www.google.com")
    self.assertEqual(story.name, "web-power-mock-story-custom")
    self.assertEqual(story.duration, dt.timedelta(seconds=123))


class WebPowerBenchmarkBaseTestCase(BaseBenchmarkTestCase):

  @property
  @override
  def benchmark_cls(self) -> type[MockWebPowerBenchmark]:
    return MockWebPowerBenchmark

  def test_kwargs_from_cli_site(self) -> None:
    parser = MockWebPowerBenchmark.add_cli_arguments(CBArgumentParser())
    args = parser.parse_args(["--site", "cnn"])
    kwargs = MockWebPowerBenchmark.kwargs_from_cli(args)
    self.assertEqual(kwargs["site_key"], "cnn")
    self.assertIsNone(kwargs["url"])

  def test_kwargs_from_cli_url(self) -> None:
    parser = MockWebPowerBenchmark.add_cli_arguments(CBArgumentParser())
    args = parser.parse_args(["--url", "https://www.google.com"])
    kwargs = MockWebPowerBenchmark.kwargs_from_cli(args)
    self.assertIsNone(kwargs["site_key"])
    self.assertEqual(kwargs["url"], "https://www.google.com")

  def test_kwargs_from_cli_missing_required(self) -> None:
    parser = MockWebPowerBenchmark.add_cli_arguments(CBArgumentParser())
    args = parser.parse_args([])
    with self.assertRaisesRegex(
        argparse.ArgumentTypeError,
        "One of the arguments --site --url is required"):
      MockWebPowerBenchmark.kwargs_from_cli(args)

  def test_kwargs_from_cli_help(self) -> None:
    parser = MockWebPowerBenchmark.add_cli_arguments(CBArgumentParser())
    # Passing --help should bypass validation and raise SystemExit natively
    with self.assertRaises(SystemExit):
      parser.parse_args(["--help"])

  def test_kwargs_from_cli_site_wpr_default(self) -> None:
    parser = MockWebPowerBenchmark.add_cli_arguments(CBArgumentParser())
    args = parser.parse_args(["--site", "cnn"])
    # Simulate CLI runner parsing network defaults
    args.network_config = None
    args.network = None
    args.has_explicit_network = False

    kwargs = MockWebPowerBenchmark.kwargs_from_cli(args)
    self.assertEqual(kwargs["site_key"], "cnn")
    # args.network should be mapped to WPR with the canonical cnn archive URL
    self.assertIsInstance(args.network, NetworkConfig)
    self.assertEqual(args.network.type, NetworkType.WPR)
    self.assertEqual(args.network.url,
                     "gs://chrome-partner-loadline/power/cnn_20260513.wprgo")

  def test_kwargs_from_cli_url_live_default(self) -> None:
    parser = MockWebPowerBenchmark.add_cli_arguments(CBArgumentParser())
    args = parser.parse_args(["--url", "https://www.google.com"])
    # Simulate CLI runner parsing network defaults
    args.network_config = None
    args.network = NetworkConfig.default()
    args.has_explicit_network = False

    kwargs = MockWebPowerBenchmark.kwargs_from_cli(args)
    self.assertEqual(kwargs["url"], "https://www.google.com")
    self.assertEqual(args.network.type, NetworkType.LIVE)

  def test_kwargs_from_cli_url_with_explicit_network(self) -> None:
    parser = MockWebPowerBenchmark.add_cli_arguments(CBArgumentParser())
    args = parser.parse_args(["--url", "https://www.google.com"])
    # Simulate explicit WPR network config
    args.network_config = None
    args.network = NetworkConfig(
        type=NetworkType.WPR, url="gs://some/other.wprgo")

    args.has_explicit_network = True

    kwargs = MockWebPowerBenchmark.kwargs_from_cli(args)
    self.assertEqual(kwargs["url"], "https://www.google.com")
    self.assertEqual(args.network.type, NetworkType.WPR)
    self.assertEqual(args.network.url, "gs://some/other.wprgo")

  def test_kwargs_from_cli_site_with_explicit_network_fails(self) -> None:
    parser = MockWebPowerBenchmark.add_cli_arguments(CBArgumentParser())
    args = parser.parse_args(["--site", "cnn"])
    # Simulate conflicting explicit network config
    args.network_config = None
    args.network = NetworkConfig(
        type=NetworkType.WPR, url="gs://some/other.wprgo")

    args.has_explicit_network = True

    with self.assertRaisesRegex(
        ValueError, "Specifying '--site' is mutually exclusive with explicit"):
      MockWebPowerBenchmark.kwargs_from_cli(args)

  def test_kwargs_from_cli_bits(self) -> None:
    bits_path = pth.LocalPath(self.platform.default_tmp_dir) / "bits"
    self.fs.create_file(bits_path)

    parser = MockWebPowerBenchmark.add_cli_arguments(CBArgumentParser())
    args = parser.parse_args([
        "--site", "cnn", "--bits-path",
        str(bits_path), "--bits-out", "custom_bits_run", "--bits-duration", "5m"
    ])
    kwargs = MockWebPowerBenchmark.kwargs_from_cli(args)
    self.assertEqual(kwargs["site_key"], "cnn")

    bits_probe = kwargs["bits_probe"]
    self.assertIsInstance(bits_probe, BitsProbe)
    self.assertEqual(bits_probe.bits_path, bits_path)
    self.assertEqual(bits_probe.bits_out, "custom_bits_run")
    self.assertEqual(bits_probe.duration, dt.timedelta(minutes=5))
    self.assertEqual(bits_probe.bits_device, "")

  def test_kwargs_from_cli_bits_with_device(self) -> None:
    bits_path = pth.LocalPath(self.platform.default_tmp_dir) / "bits"
    self.fs.create_file(bits_path)

    parser = MockWebPowerBenchmark.add_cli_arguments(CBArgumentParser())
    args = parser.parse_args([
        "--site", "cnn", "--bits-path",
        str(bits_path), "--bits-out", "custom_bits_run", "--bits-device",
        "dev_123", "--bits-duration", "5m"
    ])
    kwargs = MockWebPowerBenchmark.kwargs_from_cli(args)
    bits_probe = kwargs["bits_probe"]
    self.assertEqual(bits_probe.bits_device, "dev_123")


  def test_setup_bits_probe(self) -> None:
    bits_path = pth.LocalPath(self.platform.default_tmp_dir) / "bits"
    self.fs.create_file(bits_path)

    # Both flags provided: BitsProbe should be attached
    bits_probe = BitsProbe(
        bits_path=bits_path,
        bits_out="run_id",
        duration=dt.timedelta(seconds=120),
    )
    benchmark = MockWebPowerBenchmark(
        site_key="cnn",
        bits_probe=bits_probe,
        total_duration=dt.timedelta(seconds=123),
    )
    runner = mock.MagicMock()
    benchmark.setup(runner)
    runner.attach_probe.assert_called_once()
    attached_probe = runner.attach_probe.call_args.args[0]
    self.assertIsInstance(attached_probe, BitsProbe)
    self.assertEqual(attached_probe.bits_path, bits_path)
    self.assertEqual(attached_probe.bits_out, "run_id")
    self.assertEqual(attached_probe.duration, dt.timedelta(seconds=120))

  def test_kwargs_from_cli_bits_only_path_fails(self) -> None:
    bits_path = pth.LocalPath(self.platform.default_tmp_dir) / "bits"
    self.fs.create_file(bits_path)

    parser = MockWebPowerBenchmark.add_cli_arguments(CBArgumentParser())
    args = parser.parse_args(["--site", "cnn", "--bits-path", str(bits_path)])
    with self.assertRaises(argparse.ArgumentTypeError):
      MockWebPowerBenchmark.kwargs_from_cli(args)

  def test_kwargs_from_cli_bits_only_out_fails(self) -> None:
    parser = MockWebPowerBenchmark.add_cli_arguments(CBArgumentParser())
    args = parser.parse_args(["--site", "cnn", "--bits-out", "run_id"])
    with self.assertRaises(argparse.ArgumentTypeError):
      MockWebPowerBenchmark.kwargs_from_cli(args)

  def test_default_probe_config_path(self) -> None:
    path = MockWebPowerBenchmark.default_probe_config_path()
    self.assertIsNotNone(path)
    assert path is not None
    self.assertEqual(path.name, "probe_config.hjson")

  def test_probe_config_default_and_override(self) -> None:
    parser = CBArgumentParser()
    parser.add_argument(
        "--probe-config",
        type=pathlib.Path,
        default=MockWebPowerBenchmark.default_probe_config_path(),
    )

    # Scenario A: Default config path resolved when flag is omitted
    args_default = parser.parse_args([])
    self.assertEqual(
        args_default.probe_config,
        MockWebPowerBenchmark.default_probe_config_path(),
    )

    # Scenario B: Custom non-default config path successfully overrides default
    custom_path = pathlib.Path("/path/to/custom.hjson")
    args_custom = parser.parse_args(["--probe-config", str(custom_path)])
    self.assertEqual(args_custom.probe_config, custom_path)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
