# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import unittest
from typing import TYPE_CHECKING, Any, ClassVar, Sequence
from unittest import mock

from typing_extensions import override

from crossbench import path as pth
from crossbench import plt
from crossbench.benchmarks.web_power import wpr_helpers
from crossbench.benchmarks.web_power.base import WebPowerBenchmarkBase, \
    WebPowerSiteConfig, WebPowerStory, WebPowerStoryFilter, _value_or
from crossbench.cli.config.network import NetworkConfig, NetworkType
from crossbench.cli.parser import CBArgumentParser
from crossbench.network.replay.wpr import WprReplayNetwork
from crossbench.probes.bits import BitsProbe
from tests import test_helper
from tests.crossbench.base import BaseCrossbenchTestCase
from tests.crossbench.benchmarks.helper import BaseBenchmarkTestCase

if TYPE_CHECKING:
  from crossbench.runner.run import Run


class MockWebPowerStory(WebPowerStory):

  @classmethod
  @override
  def story_name_cls(cls) -> str:
    return "mock-story"

  def __init__(
      self,
      name_suffix: str,
      site_config: WebPowerSiteConfig,
      total_duration: dt.timedelta = dt.timedelta(seconds=123)
  ) -> None:
    super().__init__(name_suffix, site_config, total_duration)

  def run(self, run: Run) -> None:
    pass


class MockWebPowerStoryFilter(WebPowerStoryFilter[MockWebPowerStory]):
  """Mock story filter for testing."""

  STORY_CLS = MockWebPowerStory

  @override
  def stories_from_names(self,
                         names: Sequence[str]) -> tuple[MockWebPowerStory, ...]:
    return tuple(self.story_cls.from_site(name) for name in names)


class MockWebPowerBenchmark(WebPowerBenchmarkBase):
  """Mock WebPowerBenchmark for testing."""

  DEFAULT_STORY_CLS: ClassVar = MockWebPowerStory
  STORY_FILTER_CLS: ClassVar = MockWebPowerStoryFilter


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

  def test_default_repetitions(self) -> None:
    self.assertEqual(MockWebPowerBenchmark.DEFAULT_REPETITIONS, 5)

  def test_default_cool_down(self) -> None:
    self.assertEqual(MockWebPowerBenchmark.DEFAULT_COOL_DOWN,
                     dt.timedelta(minutes=2))

  def test_kwargs_from_cli_site(self) -> None:
    parser = MockWebPowerBenchmark.add_cli_arguments(CBArgumentParser())
    args = parser.parse_args(["--site", "cnn"])
    kwargs = MockWebPowerBenchmark.kwargs_from_cli(args)
    self.assertEqual(len(kwargs["stories"]), 1)
    self.assertEqual(kwargs["stories"][0].url, "https://www.cnn.com")
    self.assertEqual(kwargs["stories"][0].name, "web-power-mock-story-cnn")

  def test_kwargs_from_cli_url(self) -> None:
    parser = MockWebPowerBenchmark.add_cli_arguments(CBArgumentParser())
    args = parser.parse_args(["--url", "https://www.google.com"])
    kwargs = MockWebPowerBenchmark.kwargs_from_cli(args)
    self.assertEqual(len(kwargs["stories"]), 1)
    self.assertEqual(kwargs["stories"][0].name, "web-power-mock-story-custom")
    self.assertEqual(kwargs["stories"][0].url, "https://www.google.com")

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
    self.assertEqual(len(kwargs["stories"]), 1)
    self.assertEqual(kwargs["stories"][0].name, "web-power-mock-story-cnn")
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
    self.assertEqual(len(kwargs["stories"]), 1)
    self.assertEqual(kwargs["stories"][0].name, "web-power-mock-story-custom")
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
    self.assertEqual(len(kwargs["stories"]), 1)
    self.assertEqual(kwargs["stories"][0].name, "web-power-mock-story-custom")
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
    self.assertEqual(len(kwargs["stories"]), 1)
    self.assertEqual(kwargs["stories"][0].name, "web-power-mock-story-cnn")

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
    story = MockWebPowerStory.from_site(
        "cnn", total_duration=dt.timedelta(seconds=123))
    benchmark = MockWebPowerBenchmark(
        stories=[story],
        bits_probe=bits_probe,
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


class FakeWprReplayNetwork(WprReplayNetwork):

  def __init__(self, archive_path: pth.LocalPath,
               platform: plt.Platform) -> None:
    super().__init__(
        archive=archive_path,
        traffic_shaper=mock.MagicMock(),
        browser_platform=platform,
        persist_server=False,
        inject_deterministic_script=False,
        no_archive_certificates=True,
        response_transformations_file=None,
        cross_platform_mode=False,
        host=None,
    )
    self._server = None

  def _create_server(self, log_dir: Any) -> Any:
    return mock.MagicMock()

  @property
  @override
  def _wpr_platform(self) -> Any:
    return mock.MagicMock()


class WebPowerBenchmarkSetupSessionTestCase(BaseCrossbenchTestCase):

  def setUp(self) -> None:
    super().setUp()
    # Mock WprGoFinder.httparchive() to point to /tmp/httparchive
    wpr_go_finder_patcher = mock.patch(
        "crossbench.benchmarks.web_power.base.WprGoFinder")
    self.mock_finder = wpr_go_finder_patcher.start()
    self.addCleanup(wpr_go_finder_patcher.stop)
    self.mock_finder.return_value.httparchive.return_value = self.platform.path(
        "/tmp/httparchive")
    self.fs.create_file(self.platform.path("/tmp/httparchive"))

    # Mock prepare_gcs_request and download_gcs_file
    prepare_gcs_patcher = mock.patch.object(self.platform,
                                            "prepare_gcs_request")
    self.mock_prepare = prepare_gcs_patcher.start()
    self.addCleanup(prepare_gcs_patcher.stop)

    mock_blob = mock.MagicMock()
    mock_blob.md5_hash = "mock_hash"
    self.mock_prepare.return_value = mock_blob

    download_gcs_patcher = mock.patch.object(self.platform, "download_gcs_file")
    self.mock_download = download_gcs_patcher.start()
    self.addCleanup(download_gcs_patcher.stop)
    self.mock_download.side_effect = (
        lambda url, path: self.fs.create_file(path))

  def _create_session(
      self,
      site_key: str | None = None,
      url: str | None = None,
  ) -> tuple[MockWebPowerBenchmark, FakeWprReplayNetwork, mock.MagicMock]:
    archive_path = pth.LocalPath("/tmp/archive.wprgo")
    if not self.fs.exists(str(archive_path)):
      self.fs.create_file(archive_path)

    with mock.patch("crossbench.network.replay.wpr.WprGoFinder") as mock_finder:
      mock_finder.return_value.wpr.return_value = pth.LocalPath("/tmp/wpr")
      network = FakeWprReplayNetwork(archive_path, self.platform)
    browser = mock.MagicMock()
    browser.network = network

    if site_key:
      story = MockWebPowerStory.from_site(
          site_key, total_duration=dt.timedelta(seconds=10))
    else:
      assert url is not None
      story = MockWebPowerStory.from_url(
          url, total_duration=dt.timedelta(seconds=10))
    benchmark = MockWebPowerBenchmark(stories=[story])
    run = mock.MagicMock()
    run.story = story
    run.browser = browser

    session = mock.MagicMock()
    session.runs = [run]
    session.first_run = run
    session.is_single_run = True
    session.host_platform = self.platform
    session.network = network
    session.browser = browser

    return benchmark, network, session

  def test_setup_session_network(self) -> None:
    benchmark, network, session = self._create_session(site_key="cnn")
    self.fs.create_file(self.platform.path("/tmp/cnn_archive.wprgo"))

    with mock.patch.object(
        self.platform, "sh_stdout", return_value='{"Metadata": {}}'):
      benchmark.setup_session_network(session)
      expected_archive_path = self.platform.local_cache_dir(
          "wpr") / "cnn_20260513_mock_hash.wprgo"
      self.assertEqual(network.archive_path, expected_archive_path)
      self.assertIsNone(network._response_transformations_file)

  def test_setup_session_network_with_cookie_banner(self) -> None:
    benchmark, network, session = self._create_session(site_key="cnn")
    self.fs.create_file(self.platform.path("/tmp/cnn_archive.wprgo"))
    dismisser_file = pathlib.Path(wpr_helpers.__file__).parent / "dismisser.js"
    self.fs.add_real_file(dismisser_file)

    with mock.patch.object(
        self.platform,
        "sh_stdout",
        return_value=('Dismisser target: button,button,"Accept All",'
                      'https://www.cnn.com')):
      benchmark.setup_session_network(session)
      expected_archive_path = self.platform.local_cache_dir(
          "wpr") / "cnn_20260513_mock_hash.wprgo"
      self.assertEqual(network.archive_path, expected_archive_path)
      self.assertIsNotNone(network._response_transformations_file)
      rules_file = network._response_transformations_file
      assert rules_file is not None
      self.assertTrue(pathlib.Path(rules_file).exists())

  def test_setup_session_network_twice(self) -> None:
    benchmark, network, session1 = self._create_session(site_key="cnn")
    _, _, session2 = self._create_session(site_key="cnn")
    session2.network = network

    cnn_archive = self.platform.path("/tmp/cnn_archive.wprgo")
    self.fs.create_file(cnn_archive)

    with mock.patch.object(
        self.platform, "sh_stdout", return_value='{"Metadata": {}}'):
      benchmark.setup_session_network(session1)
      with network.open(session1):
        self.assertIsNotNone(network._server)
      self.assertIsNone(network._server)

      benchmark.setup_session_network(session2)
      with network.open(session2):
        self.assertIsNotNone(network._server)
      self.assertIsNone(network._server)

  def test_setup_session_network_different_predefined_sites(self) -> None:
    benchmark1, network, session1 = self._create_session(site_key="cnn")
    benchmark2, _, session2 = self._create_session(site_key="youtube")
    session2.network = network

    self.fs.create_file(self.platform.path("/tmp/cnn_archive.wprgo"))
    self.fs.create_file(self.platform.path("/tmp/youtube_archive.wprgo"))

    with mock.patch.object(
        self.platform, "sh_stdout", return_value='{"Metadata": {}}'):
      # Setup and run cnn
      benchmark1.setup_session_network(session1)
      expected_cnn_path = self.platform.local_cache_dir(
          "wpr") / "cnn_20260513_mock_hash.wprgo"
      self.assertEqual(network.archive_path, expected_cnn_path)
      with network.open(session1):
        self.assertIsNotNone(network._server)
      self.assertIsNone(network._server)

      # Setup and run youtube (should update archive path!)
      benchmark2.setup_session_network(session2)
      expected_youtube_path = self.platform.local_cache_dir(
          "wpr") / "youtube_2026_05_18_mock_hash.wprgo"
      self.assertEqual(network.archive_path, expected_youtube_path)
      with network.open(session2):
        self.assertIsNotNone(network._server)
      self.assertIsNone(network._server)

  def test_setup_session_network_custom_wpr(self) -> None:
    archive_path = pth.LocalPath("/tmp/custom_archive.wprgo")
    self.fs.create_file(archive_path)

    benchmark, network, session = self._create_session(
        url="https://www.google.com")
    network.set_archive_path(archive_path)

    dismisser_file = pathlib.Path(wpr_helpers.__file__).parent / "dismisser.js"
    self.fs.add_real_file(dismisser_file)

    with mock.patch.object(
        self.platform,
        "sh_stdout",
        return_value=('Dismisser target: button,button,"Accept All",'
                      'https://www.google.com')):
      benchmark.setup_session_network(session)
      self.assertEqual(network.archive_path, archive_path)
      self.assertIsNotNone(network._response_transformations_file)
      rules_file = network._response_transformations_file
      assert rules_file is not None
      self.assertTrue(pathlib.Path(rules_file).exists())


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
