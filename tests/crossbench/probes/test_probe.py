# Copyright 2024 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from __future__ import annotations

import abc
import inspect
from typing import TYPE_CHECKING
from unittest import mock

from typing_extensions import override

import crossbench.path as pth
from crossbench.browsers.settings import Settings
from crossbench.cli.config.probe_list import ProbeListConfig
from crossbench.probes.all import CONFIGURABLE_INTERNAL_PROBES, \
    DEFAULT_INTERNAL_PROBES, GENERAL_PURPOSE_PROBES, INTERNAL_PROBES, \
    NON_CONFIGURABLE_INTERNAL_PROBES, OPTIONAL_INTERNAL_PROBES
from crossbench.probes.bits import BitsProbe
from crossbench.probes.cb_perfetto.perfetto import PerfettoProbe
from crossbench.probes.cb_perfetto.tracing import TracingProbe
from crossbench.probes.chrome_histograms import ChromeHistogramsProbe
from crossbench.probes.chromium_pgo import ChromiumPgoProbe
from crossbench.probes.chromium_probe import ChromiumProbe
from crossbench.probes.debugger import DebuggerProbe
from crossbench.probes.downloads import DownloadsProbe
from crossbench.probes.dtrace import DTraceProbe
from crossbench.probes.dump_heap import DumpHeapProbe
from crossbench.probes.dump_html import DumpHtmlProbe
from crossbench.probes.embedder import WebviewEmbedderProbe
from crossbench.probes.env_modifier import EnvModifier
from crossbench.probes.etm import EtmProbe
from crossbench.probes.frequency import FrequencyProbe
from crossbench.probes.js import JSProbe
from crossbench.probes.json import JsonResultProbe
from crossbench.probes.metrics_internals import ChromeMetricsInternalsProbe
from crossbench.probes.performance_entries import PerformanceEntriesProbe
from crossbench.probes.polling import PollingShellProbe
from crossbench.probes.power_sampler import PowerSamplerProbe
from crossbench.probes.powermetrics import PowerMetricsProbe
from crossbench.probes.probe import Probe, ProbeKeyT, ProbePriority
from crossbench.probes.probe_error import ProbeIncompatibleBrowser, \
    ProbeValidationError
from crossbench.probes.profiling.browser_profiling import BrowserProfilingProbe
from crossbench.probes.profiling.system_profiling import ProfilingProbe
from crossbench.probes.results import LocalProbeResult
from crossbench.probes.screenshot import ScreenshotProbe
from crossbench.probes.shell import LocalShellProbe, ShellProbe, ShellProbeBase
from crossbench.probes.system_stats import SystemStatsProbe
from crossbench.probes.trace_processor.trace_processor import \
    TraceProcessorProbe
from crossbench.probes.v8.builtins_pgo import V8BuiltinsPGOProbe
from crossbench.probes.v8.log import V8LogProbe
from crossbench.probes.v8.rcs import V8RCSProbe
from crossbench.probes.v8.turbolizer import V8TurbolizerProbe
from crossbench.probes.video import VideoProbe
from crossbench.probes.web_page_replay.recorder import WebPageReplayProbe
from tests import test_helper
from tests.crossbench.base import CrossbenchConfigTestMixin, \
    CrossbenchFakeFsTestCase
from tests.crossbench.mock_browser import MockChromeStable
from tests.crossbench.mock_helper import LinuxMockPlatform
from tests.crossbench.probes.helper import BaseProbeTestCase

if TYPE_CHECKING:
  from tests.crossbench.mock_helper import MockPlatform
  from tests.crossbench.runner.helper import MockRun


class ProbeListConfigTestCase(CrossbenchFakeFsTestCase):

  def test_invalid_empty(self):
    with self.assertRaisesRegex(ValueError, "str"):
      ProbeListConfig.parse({"probes": ""})
    with self.assertRaisesRegex(ValueError, "probes"):
      ProbeListConfig.parse({"browsers": {}})

  def test_empty(self):
    probe_list = ProbeListConfig.parse({"probes": []})
    self.assertEqual(probe_list.probes, ())
    probe_list = ProbeListConfig.parse({"probes": {}})
    self.assertEqual(probe_list.probes, ())


class ProbeTestCase(CrossbenchConfigTestMixin, CrossbenchFakeFsTestCase):

  def setUp(self) -> None:
    super().setUp()
    self.setup_perfetto_config_presets()

  def probe_instances(self):
    yield from self.internal_probe_instances()
    yield from self.general_purpose_probe_instances()

  def internal_probe_instances(self):
    for probe_cls in INTERNAL_PROBES:
      yield probe_cls()

  def general_purpose_probe_instances(self):
    yield BrowserProfilingProbe()
    yield ChromiumPgoProbe()
    yield DTraceProbe(pth.LocalPath("script.dtrace"))
    yield DebuggerProbe(pth.LocalPath("debugger.bin"))
    yield DownloadsProbe()
    yield DumpHtmlProbe()
    yield DumpHeapProbe()
    yield FrequencyProbe.parse_dict({})
    yield PerfettoProbe(enabled_tags=["v8"])
    yield PerformanceEntriesProbe()
    yield PowerMetricsProbe()
    yield PowerSamplerProbe()
    yield ProfilingProbe()
    yield ScreenshotProbe()
    yield PollingShellProbe(cmd=["ls"])
    yield SystemStatsProbe()
    yield TracingProbe()
    yield V8BuiltinsPGOProbe()
    yield V8LogProbe()
    yield V8RCSProbe()
    yield V8TurbolizerProbe()
    yield VideoProbe()
    yield WebPageReplayProbe()

  def probe_classes(self):
    yield from INTERNAL_PROBES
    yield from GENERAL_PURPOSE_PROBES

  def test_general_purpose_probe_order(self):
    sorted_probe_classes = sorted(GENERAL_PURPOSE_PROBES, key=lambda x: x.NAME)
    self.assertSequenceEqual(GENERAL_PURPOSE_PROBES, sorted_probe_classes)

  def all_probe_subclasses(self, probe_cls=Probe):
    for probe_sub_cls in probe_cls.__subclasses__():
      if "Mock" in str(probe_sub_cls):
        continue
      # Only yield concrete probe classes (while still recursing into their
      # subclasses).
      # We must also manually exclude specific helper base classes that are
      # "conceptually abstract" but technically concrete. (Not ever expected
      # to be instantiated, but don't actually possess @abc.abstractmethod
      # methods that'd trigger isabstract.)
      if (not inspect.isabstract(probe_sub_cls) and
          probe_sub_cls not in (ChromiumProbe, EnvModifier, JsonResultProbe)):
        yield probe_sub_cls
      yield from self.all_probe_subclasses(probe_sub_cls)
    yield from OPTIONAL_INTERNAL_PROBES

  def test_properties(self):
    for probe_cls in INTERNAL_PROBES:
      with self.subTest(probe_cls=str(probe_cls)):
        self.assertFalse(probe_cls.IS_GENERAL_PURPOSE)

    for probe_cls in GENERAL_PURPOSE_PROBES:
      with self.subTest(probe_cls=str(probe_cls)):
        self.assertTrue(probe_cls.IS_GENERAL_PURPOSE)

    for probe_cls in self.probe_classes():
      with self.subTest(probe_cls=str(probe_cls)):
        self.assertTrue(probe_cls.NAME)

  def test_default_lists(self):
    count = 0
    for probe_cls in self.all_probe_subclasses():
      count += 1
      if probe_cls.IS_GENERAL_PURPOSE:
        self.assertIn(probe_cls, GENERAL_PURPOSE_PROBES)
    self.assertGreater(
        count,
        len(GENERAL_PURPOSE_PROBES) + len(DEFAULT_INTERNAL_PROBES))
    self.assertFalse(
        set(NON_CONFIGURABLE_INTERNAL_PROBES).intersection(
            set(CONFIGURABLE_INTERNAL_PROBES)))
    self.assertFalse(
        set(NON_CONFIGURABLE_INTERNAL_PROBES).intersection(
            set(OPTIONAL_INTERNAL_PROBES)))
    self.assertFalse(
        set(CONFIGURABLE_INTERNAL_PROBES).intersection(
            set(OPTIONAL_INTERNAL_PROBES)))

  def test_help(self):
    for probe_cls in self.probe_classes():
      help_text = probe_cls.help_text()
      self.assertTrue(help_text)
      summary = probe_cls.summary_text()
      self.assertTrue(summary)
      self.assertIn(summary, help_text)

  def test_config_parser(self):
    for probe_cls in self.probe_classes():
      config_parser = probe_cls.config_parser()
      self.assertEqual(config_parser.probe_cls, probe_cls)
      self.assertIn(probe_cls.NAME, config_parser.title)

  def test_config_parser_defaults(self):
    # If possible all probes should define a sane default so they can easily
    # be experimented with and make it more accessible to explore.
    # TODO(crbug.com/383572680): provide more default settings
    requires_configuration = {
        ChromeHistogramsProbe,
        ChromeMetricsInternalsProbe,
        DTraceProbe,
        # Reason: missing lldb binary on some platforms
        DebuggerProbe,
        # TODO: provide default settings
        JSProbe,
        # TODO: auto-download perfetto bin from storage
        PerfettoProbe,
        # TODO: provide default settings
        PollingShellProbe,
        # TODO: provide default settings
        ShellProbe,
        LocalShellProbe,
        # TODO: missing wpr, download precompiled wpr from storage
        WebPageReplayProbe,
        WebviewEmbedderProbe,
        EtmProbe,
        # Reason: requires bits_path and bits_out parameters
        BitsProbe,
    }
    for probe_cls in GENERAL_PURPOSE_PROBES:
      if probe_cls in requires_configuration:
        continue
      config_parser = probe_cls.config_parser()
      probe = config_parser.parse({})
      self.assertIsInstance(probe, probe_cls)

  def test_basic_probe_instances(self):
    keys: set[ProbeKeyT] = set()
    names: set[str] = set()
    for probe_instance in self.probe_instances():
      _ = hash(probe_instance)
      key = probe_instance.key
      self.assertIsInstance(key, tuple)
      self.assertNotIn(key, keys)
      keys.add(key)
      self.assertTrue(probe_instance.name)
      self.assertNotIn(probe_instance.name, names)
      names.add(probe_instance.name)

  def test_is_internal(self):
    for probe_instance in self.internal_probe_instances():
      with self.subTest(probe_cls=str(type(probe_instance))):
        self.assertTrue(probe_instance.is_internal)
        self.assertEqual(probe_instance.PRIORITY, ProbePriority.INTERNAL)

    for probe_instance in self.general_purpose_probe_instances():
      with self.subTest(probe_cls=str(type(probe_instance))):
        self.assertFalse(probe_instance.is_internal)

  def test_is_attached(self):
    for probe_instance in self.general_purpose_probe_instances():
      with self.subTest(probe_cls=str(type(probe_instance))):
        self.assertFalse(probe_instance.is_attached)

  def test_probe_priority(self):
    for probe_cls in INTERNAL_PROBES:
      self.assertEqual(probe_cls.PRIORITY, ProbePriority.INTERNAL)

    for probe_cls in GENERAL_PURPOSE_PROBES:
      with self.subTest(probe_cls=str(probe_cls)):
        if probe_cls == TraceProcessorProbe:
          self.assertEqual(probe_cls.PRIORITY, ProbePriority.TRACE_PROCESSOR)
        elif probe_cls == ChromeHistogramsProbe:
          self.assertEqual(probe_cls.PRIORITY, ProbePriority.PRE_USER)
        else:
          self.assertEqual(probe_cls.PRIORITY, ProbePriority.USER)

  def _verify_shell_probe_key(self, probe_cls: type[ShellProbeBase]) -> None:
    probe = probe_cls()
    cmd_keys = [k for k, _ in probe.key if k.endswith("_cmd")]

    base_kwargs = {k: (k,) for k in cmd_keys}
    probe = probe_cls(**base_kwargs)

    self.assertEqual(probe.key[0], ("name", probe_cls.NAME))

    key_dict = dict(probe.key)
    for k, val in base_kwargs.items():
      self.assertIn(k, key_dict)
      self.assertEqual(key_dict[k], val)

  def test_shell_probe_key(self):
    self._verify_shell_probe_key(ShellProbe)

  def test_local_shell_probe_key(self):
    self._verify_shell_probe_key(LocalShellProbe)

  def test_probe_incompatible_browser_message(self):
    probe = BrowserProfilingProbe()
    platform = LinuxMockPlatform()
    MockChromeStable.setup_fs(self.fs, platform)
    browser = MockChromeStable("stable", settings=Settings(platform=platform))
    self.assertRegex(
        str(ProbeIncompatibleBrowser(probe, browser, "Some error message")),
        r"Probe\(browser-profiling\): Some error message\n"
        r"      Got: browser=Chrome:stable, "
        r"platform=local\.mock\.linux\.arm64\.\d+")


class ShellProbeExecutionTestCase(BaseProbeTestCase):

  def _verify_shell_probe_execution(self, probe_cls: type[ShellProbeBase],
                                    run: MockRun,
                                    target_platform: MockPlatform) -> None:
    cmds = {
        "setup_cmd": ["setup-cmd", "1", "2"],
        "start_cmd": ["start-cmd", "3", "4"],
        "start_story_run_cmd": ["start-story-cmd", "5", "6"],
        "stop_story_run_cmd": ["stop-story-cmd", "7", "8"],
        "stop_cmd": ["stop-cmd", "9", "10"],
        "teardown_cmd": ["teardown-cmd", "11", "12"],
    }
    probe = probe_cls(**cmds)

    # MockPlatform.expect_sh pre-registers expected commands in a FIFO queue.
    # MockPlatform.sh() will assert that these commands are executed in this
    # exact sequential order at runtime, failing immediately on any mismatch.
    # That is, reordering these WILL result in a failure, as expected.
    for cmd in cmds.values():
      target_platform.expect_sh(*cmd)

    context = probe.create_context(run)

    context.setup()
    context.start()
    context.start_story_run()
    context.stop_story_run()
    context.stop()
    result = context.teardown()

    self.assertIsInstance(result, LocalProbeResult)

    # Verify the exact filenames are constructed correctly from hook names.
    expected_filenames = [
        f"{key.removesuffix('_cmd')}.{suffix}.txt" for key in cmds
        for suffix in ("stdout", "stderr")
    ]
    actual_filenames = [f.name for f in result.file_list]
    self.assertListEqual(actual_filenames, expected_filenames)

    # Verify that no pending expected commands remain unexecuted.
    self.assertListEqual(target_platform.sh_results, [])

  def test_browser_shell_probe_execution(self):
    run = self.mock_run()
    browser_platform = self.setup_platform()
    run.browser_session.browser.platform = browser_platform
    self._verify_shell_probe_execution(ShellProbe, run, browser_platform)

  def test_local_shell_probe_execution(self):
    run = self.mock_run()
    self._verify_shell_probe_execution(LocalShellProbe, run, self.platform)


class BaseShellProbeValidationTestCase(BaseProbeTestCase):
  """The validation logic is mostly equivalent for both local and remote
  platforms, so we share the test cases in this base class and specialize
  the concrete subclasses for LocalShellProbe and ShellProbe.
  """
  __test__ = False

  @property
  @abc.abstractmethod
  def probe_cls(self) -> type[ShellProbeBase]:
    pass

  def _create_file(self, path_str: str, st_mode: int) -> pth.AnyPath:
    path = pth.AnyPath(path_str)
    self.fs.create_file(path, st_mode=st_mode)
    return path

  @override
  def setUp(self) -> None:
    super().setUp()
    self._local_exec_1 = self._create_file("/local/bin/local_exec_1", 0o755)
    self._local_exec_2 = self._create_file("/local/bin/local_exec_2", 0o755)
    self._local_non_exec = self._create_file("/local/bin/local_non_exec", 0o644)

    self._remote_exec_1 = self._create_file("/remote/bin/remote_exec_1", 0o755)
    self._remote_exec_2 = self._create_file("/remote/bin/remote_exec_2", 0o755)
    self._remote_non_exec = self._create_file("/remote/bin/remote_non_exec",
                                              0o644)

    run = self.mock_run()
    self.browser = run.browser
    self.browser_platform = self.setup_platform()
    self.browser_platform.use_fs = True
    self.browser.platform = self.browser_platform

    # Register lookups permanently for host platform.
    self.browser.host_platform.set_binary_lookup_override(
        "local_exec_1", self._local_exec_1)
    self.browser.host_platform.set_binary_lookup_override(
        "local_exec_2", self._local_exec_2)

    # Register lookups permanently for browser/remote platform.
    self.browser_platform.set_binary_lookup_override("remote_exec_1",
                                                     self._remote_exec_1)
    self.browser_platform.set_binary_lookup_override("remote_exec_2",
                                                     self._remote_exec_2)

    self.prefix = "local" if self.probe_cls is LocalShellProbe else "remote"
    wrong_prefix = "remote" if self.probe_cls is LocalShellProbe else "local"

    self.exec_1 = f"{self.prefix}_exec_1"
    self.exec_2 = f"{self.prefix}_exec_2"
    self.non_exec = getattr(self, f"_{self.prefix}_non_exec")
    self.typo = f"{self.prefix}_exec_typo"
    self.wrong_exec = f"{wrong_prefix}_exec_1"

  def _verify_validation(self, probe: ShellProbeBase) -> None:
    probe.validate_browser(mock.MagicMock(), self.browser)

  def test_validation_success(self):
    probe = self.probe_cls(setup_cmd=[self.exec_1], stop_cmd=[self.exec_2])
    self._verify_validation(probe)

  def test_validation_not_executable(self):
    probe = self.probe_cls(setup_cmd=[self.non_exec], stop_cmd=[self.exec_2])
    with self.assertRaises(ProbeValidationError) as cm:
      self._verify_validation(probe)
    self.assertIn("not executable or does not exist", str(cm.exception))

  def test_validation_typo(self):
    probe = self.probe_cls(setup_cmd=[self.typo], stop_cmd=[self.exec_2])
    with self.assertRaises(ProbeValidationError) as cm:
      self._verify_validation(probe)
    self.assertIn("not executable or does not exist", str(cm.exception))

  def test_validation_wrong_platform_path(self):
    probe = self.probe_cls(setup_cmd=[self.wrong_exec], stop_cmd=[self.exec_2])
    with self.assertRaises(ProbeValidationError) as cm:
      self._verify_validation(probe)
    self.assertIn("not executable or does not exist", str(cm.exception))

  def test_validation_tilde_success(self):
    probe = self.probe_cls()
    target_platform = probe.target_platform(self.browser)

    home_dir = target_platform.home()
    exec_path = home_dir / f"{self.prefix}_exec_tilde"
    self._create_file(str(exec_path), 0o755)
    # Binary lookup override is needed because shutil.which doesn't search
    # outside PATH. We mock the lookup for the expanded path.
    target_platform.set_binary_lookup_override(str(exec_path), exec_path)

    probe = self.probe_cls(
        setup_cmd=[f"~/{self.prefix}_exec_tilde"], stop_cmd=[self.exec_2])
    self._verify_validation(probe)

  def test_validation_tilde_failure_non_existent(self):
    probe = self.probe_cls(
        setup_cmd=[f"~/{self.prefix}_does_not_exist_tilde"],
        stop_cmd=[self.exec_2])
    with self.assertRaises(ProbeValidationError) as cm:
      self._verify_validation(probe)
    self.assertIn("not executable or does not exist", str(cm.exception))


class LocalShellProbeValidationTestCase(BaseShellProbeValidationTestCase):
  __test__ = True

  @property
  def probe_cls(self) -> type[LocalShellProbe]:
    return LocalShellProbe


class RemoteShellProbeValidationTestCase(BaseShellProbeValidationTestCase):
  __test__ = True

  @property
  def probe_cls(self) -> type[ShellProbe]:
    return ShellProbe


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
