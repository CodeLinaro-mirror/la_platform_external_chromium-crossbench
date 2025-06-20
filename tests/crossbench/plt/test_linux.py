# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import pathlib
import textwrap
from unittest import mock

from pyfakefs.fake_filesystem import OSType
from typing_extensions import override

from crossbench.plt.linux import parse_display_xrandr
from crossbench.plt.process_meminfo import ProcessMeminfo
from tests import test_helper
from tests.crossbench.mock_helper import (LinuxMockPlatform,
                                          RemoteLinuxMockPlatform, ShResult)
from tests.crossbench.plt.helper import (BaseLocalMockPlatformTestMixin,
                                         BasePosixMockPlatformTestCase)


class LinuxMockPlatformTestCase(BaseLocalMockPlatformTestMixin,
                                BasePosixMockPlatformTestCase):
  __test__ = True

  @override
  def setUp(self) -> None:
    super().setUp()
    self.fs.os = OSType.LINUX

  @override
  def mock_platform_setup(self) -> None:
    self.mock_platform = LinuxMockPlatform()
    self.platform = self.mock_platform

  def test_name(self):
    self.assertEqual(self.platform.name, "mock.linux")

  def test_is_linux(self):
    self.assertTrue(self.platform.is_linux)

  @mock.patch("psutil.cpu_count")
  def test_cpu_cores(self, mock_cpu_count):
    mock_cpu_count.return_value = 12
    self.assertEqual(self.platform.cpu_cores(logical=True), 12)
    mock_cpu_count.assert_called_once()

    mock_cpu_count.return_value = 6
    self.assertEqual(self.platform.cpu_cores(logical=False), 6)
    self.assertEqual(mock_cpu_count.call_count, 2)

  def test_parse_display_xrandr(self):
    xrandr_output = textwrap.dedent("""
      Screen 0: minimum 64 x 64, current 1728 x 946, maximum 32767 x 32767
      DUMMY0 connected primary 1728x946+0+0 456mm x 249mm
        1024x768      60.00  
        800x600       60.32    56.25  
        640x480       59.94  
        1600x1200_60  60.00  
        1600x1200_120 120.00  
        CRD_78       120.00*+
      DUMMY1 disconnected
        5120x1440_120 120.00  
        2160x3840_120 120.00  
      """)
    parsed = tuple(parse_display_xrandr(xrandr_output))
    self.assertEqual(len(parsed), 1)
    self.assertDictEqual(parsed[0], {
        "resolution": (1728, 946),
        "refresh_rate": 120.0
    })

  def test_meminfo_no_proc(self):

    process_name: str = "some_process"

    self.mock_platform.expect_sh("pgrep", "-f", process_name, result="")

    meminfo = self.mock_platform.meminfo(process_name)

    self.assertEqual(len(meminfo), 0)

  _SMAPS_ROLLUP_DATA = """
241800000000-7ffc064d5000 ---p 00000000 00:00 0                          [rollup]
Rss:               19792 kB
Pss:                2062 kB
Pss_Dirty:          1831 kB
Pss_Anon:           1831 kB
Pss_File:            231 kB
Pss_Shmem:             0 kB
Shared_Clean:       3932 kB
Shared_Dirty:      15604 kB
Private_Clean:         0 kB
Private_Dirty:       256 kB
Referenced:         4300 kB
Anonymous:         15860 kB
KSM:                   0 kB
LazyFree:              0 kB
AnonHugePages:      2048 kB
ShmemPmdMapped:        0 kB
FilePmdMapped:         0 kB
Shared_Hugetlb:        0 kB
Private_Hugetlb:       0 kB
Swap:                  0 kB
SwapPss:               0 kB
Locked:                0 kB
"""

  def test_meminfo(self):

    process_name: str = "some_process"

    proc_100_cmdline = "/usr/bin/some_process --some-flag"
    proc_6_cmdline = "/usr/bin/some_process --some-other-flag"
    proc_20_cmdline = "/usr/bin/some_process --some-third-flag"

    pathlib.Path("/proc/100").mkdir(parents=True)
    pathlib.Path("/proc/6").mkdir(parents=True)
    pathlib.Path("/proc/20").mkdir(parents=True)

    pathlib.Path("/proc/100/cmdline").write_text(proc_100_cmdline)
    pathlib.Path("/proc/100/smaps_rollup").write_text(self._SMAPS_ROLLUP_DATA)

    pathlib.Path("/proc/6/cmdline").write_text(proc_6_cmdline)
    pathlib.Path("/proc/6/smaps_rollup").write_text(self._SMAPS_ROLLUP_DATA)

    pathlib.Path("/proc/20/cmdline").write_text(proc_20_cmdline)
    pathlib.Path("/proc/20/smaps_rollup").write_text(self._SMAPS_ROLLUP_DATA)

    self.mock_platform.expect_sh(
        "pgrep", "-f", process_name, result="100\n6\n20\n")

    meminfo = self.mock_platform.meminfo(process_name)

    self.assertEqual(len(meminfo), 3)
    self.assertTrue(proc_100_cmdline in meminfo)
    self.assertEqual(meminfo[proc_100_cmdline],
                     ProcessMeminfo(100, 2062, 19792, 0))
    self.assertEqual(meminfo[proc_6_cmdline], ProcessMeminfo(6, 2062, 19792, 0))
    self.assertEqual(meminfo[proc_20_cmdline],
                     ProcessMeminfo(20, 2062, 19792, 0))

  def test_meminfo_missing_proc(self):
    process_name: str = "some_process"

    proc_100_cmdline = "/usr/bin/some_process --some-flag"

    pathlib.Path("/proc/100").mkdir(parents=True)
    pathlib.Path("/proc/100/cmdline").write_text(proc_100_cmdline)
    pathlib.Path("/proc/100/smaps_rollup").write_text(self._SMAPS_ROLLUP_DATA)

    self.mock_platform.expect_sh("pgrep", "-f", process_name, result="100\n6\n")

    meminfo = self.mock_platform.meminfo(process_name)

    self.assertEqual(len(meminfo), 1)
    self.assertTrue(proc_100_cmdline in meminfo)
    self.assertEqual(meminfo[proc_100_cmdline],
                     ProcessMeminfo(100, 2062, 19792, 0))

  def test_meminfo_missing_smaps(self):
    process_name: str = "some_process"
    proc_100_cmdline = "/usr/bin/some_process --some-flag"
    proc_6_cmdline = "/usr/bin/some_process --another-flag"

    pathlib.Path("/proc/100").mkdir(parents=True)
    pathlib.Path("/proc/100/cmdline").write_text(proc_100_cmdline)
    pathlib.Path("/proc/100/smaps_rollup").write_text(self._SMAPS_ROLLUP_DATA)

    pathlib.Path("/proc/6").mkdir(parents=True)
    pathlib.Path("/proc/6/cmdline").write_text(proc_6_cmdline)

    self.mock_platform.expect_sh("pgrep", "-f", process_name, result="100\n6\n")

    meminfo = self.mock_platform.meminfo(process_name)

    self.assertEqual(len(meminfo), 1)
    self.assertTrue(proc_100_cmdline in meminfo)
    self.assertEqual(meminfo[proc_100_cmdline],
                     ProcessMeminfo(100, 2062, 19792, 0))


class RemoteLinuxMockPlatformTestCase(LinuxMockPlatformTestCase):

  @override
  def mock_platform_setup(self) -> None:
    self.host_platform = LinuxMockPlatform()
    self.mock_platform = RemoteLinuxMockPlatform(self.host_platform)
    self.platform = self.mock_platform

  def cpu_info(self, processor_id, physical_id, core_id):
    return textwrap.dedent(f"""
        processor       : {processor_id}
        vendor_id       : GenuineIntel
        cpu family      : 1
        model           : 12
        model name      : Intel(R) Xeon(R) 3456 CPU @ 7.80GHz
        stepping        : 9
        microcode       : 0x123456
        cpu MHz         : 1234.000
        cache size      : 3456 KB
        physical id     : {physical_id}
        core id         : {core_id}
        fpu             : yes
        fpu_exception   : yes
        cpuid level     : 12
        wp              : yes
      """)

  def expect_sh_cpu_info(self, cpu_info):
    self.expect_sh(
        "grep",
        "-E",
        "processor|core id|physical id",
        "/proc/cpuinfo",
        result=cpu_info)

  @override
  def test_cpu_cores(self):
    single_core_info = self.cpu_info(0, 0, 0)
    self.expect_sh_cpu_info(single_core_info)
    self.assertEqual(self.platform.cpu_cores(logical=True), 1)
    self.assertFalse(self.platform.expected_sh_cmds)
    # Check that caching works.
    self.assertEqual(self.platform.cpu_cores(logical=True), 1)

    self.expect_sh_cpu_info(single_core_info)
    self.assertEqual(self.platform.cpu_cores(logical=False), 1)
    self.assertFalse(self.platform.expected_sh_cmds)
    self.assertEqual(self.platform.cpu_cores(logical=False), 1)

  def test_cpu_cores_2_cpu_single_core(self):
    # 2 physical chips, 1 core, 2 threads
    dual_chip_result = (
        self.cpu_info(0, 0, 0) + self.cpu_info(1, 0, 0) +
        self.cpu_info(2, 1, 0) + self.cpu_info(3, 1, 0))
    self.expect_sh_cpu_info(dual_chip_result)
    self.assertEqual(self.platform.cpu_cores(logical=True), 4)
    self.assertFalse(self.platform.expected_sh_cmds)
    self.assertEqual(self.platform.cpu_cores(logical=True), 4)

    self.expect_sh_cpu_info(dual_chip_result)
    self.assertEqual(self.platform.cpu_cores(logical=False), 2)
    self.assertFalse(self.platform.expected_sh_cmds)
    self.assertEqual(self.platform.cpu_cores(logical=False), 2)

  def test_cpu_cores_1_cpu_dual_core(self):
    # 1 physical chips, 2 cores, 2 threads
    dual_core_result = (
        self.cpu_info(0, 0, 0) + self.cpu_info(1, 0, 1) +
        self.cpu_info(2, 0, 0) + self.cpu_info(3, 0, 1))
    self.expect_sh_cpu_info(dual_core_result)
    self.assertEqual(self.platform.cpu_cores(logical=True), 4)
    self.assertFalse(self.platform.expected_sh_cmds)
    self.assertEqual(self.platform.cpu_cores(logical=True), 4)

    self.expect_sh_cpu_info(dual_core_result)
    self.assertEqual(self.platform.cpu_cores(logical=False), 2)
    self.assertFalse(self.platform.expected_sh_cmds)
    self.assertEqual(self.platform.cpu_cores(logical=False), 2)

  @override
  def test_meminfo(self):
    process_name: str = "some_process"

    proc_100_cmdline = "/usr/bin/some_process --some-flag"
    proc_6_cmdline = "/usr/bin/some_process --some-other-flag"
    proc_20_cmdline = "/usr/bin/some_process --some-third-flag"

    self.mock_platform.expect_sh(
        "pgrep", "-f", process_name, result="100\n6\n20\n")

    self.mock_platform.expect_sh(
        "cat", "/proc/100/cmdline", result=proc_100_cmdline)
    self.mock_platform.expect_sh(
        "cat", "/proc/100/smaps_rollup", result=self._SMAPS_ROLLUP_DATA)
    self.mock_platform.expect_sh(
        "cat", "/proc/6/cmdline", result=proc_6_cmdline)
    self.mock_platform.expect_sh(
        "cat", "/proc/6/smaps_rollup", result=self._SMAPS_ROLLUP_DATA)
    self.mock_platform.expect_sh(
        "cat", "/proc/20/cmdline", result=proc_20_cmdline)
    self.mock_platform.expect_sh(
        "cat", "/proc/20/smaps_rollup", result=self._SMAPS_ROLLUP_DATA)

    meminfo = self.mock_platform.meminfo(process_name)

    self.assertEqual(len(meminfo), 3)
    self.assertTrue(proc_100_cmdline in meminfo)
    self.assertEqual(meminfo[proc_100_cmdline],
                     ProcessMeminfo(100, 2062, 19792, 0))
    self.assertEqual(meminfo[proc_6_cmdline], ProcessMeminfo(6, 2062, 19792, 0))
    self.assertEqual(meminfo[proc_20_cmdline],
                     ProcessMeminfo(20, 2062, 19792, 0))

  @override
  def test_meminfo_missing_proc(self):
    process_name: str = "some_process"

    proc_100_cmdline = "/usr/bin/some_process --some-flag"

    self.mock_platform.expect_sh("pgrep", "-f", process_name, result="100\n6\n")
    self.mock_platform.expect_sh(
        "cat", "/proc/100/cmdline", result=proc_100_cmdline)
    self.mock_platform.expect_sh(
        "cat", "/proc/100/smaps_rollup", result=self._SMAPS_ROLLUP_DATA)

    self.mock_platform.expect_sh(
        "cat", "/proc/6/cmdline", result=ShResult("", False))

    meminfo = self.mock_platform.meminfo(process_name)

    self.assertEqual(len(meminfo), 1)
    self.assertTrue(proc_100_cmdline in meminfo)
    self.assertEqual(meminfo[proc_100_cmdline],
                     ProcessMeminfo(100, 2062, 19792, 0))

  @override
  def test_meminfo_missing_smaps(self):
    process_name: str = "some_process"
    proc_100_cmdline = "/usr/bin/some_process --some-flag"
    proc_6_cmdline = "/usr/bin/some_process --another-flag"

    self.mock_platform.expect_sh("pgrep", "-f", process_name, result="100\n6\n")
    self.mock_platform.expect_sh(
        "cat", "/proc/100/cmdline", result=proc_100_cmdline)
    self.mock_platform.expect_sh(
        "cat", "/proc/100/smaps_rollup", result=self._SMAPS_ROLLUP_DATA)
    self.mock_platform.expect_sh(
        "cat", "/proc/6/cmdline", result=proc_6_cmdline)
    self.mock_platform.expect_sh(
        "cat", "/proc/6/smaps_rollup", result=ShResult("", False))

    meminfo = self.mock_platform.meminfo(process_name)

    self.assertEqual(len(meminfo), 1)
    self.assertTrue(proc_100_cmdline in meminfo)
    self.assertEqual(meminfo[proc_100_cmdline],
                     ProcessMeminfo(100, 2062, 19792, 0))

  # TODO: implement more mock tests
  def test_local_reverse_port_forward_invalid(self):
    pass

  def test_local_reverse_port_forward(self):
    pass

  def test_local_port_forward(self):
    pass


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
