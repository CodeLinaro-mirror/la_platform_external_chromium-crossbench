# Copyright 2025 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import textwrap
from unittest import mock

from pyfakefs.fake_filesystem import OSType
from typing_extensions import override

from tests import test_helper
from tests.crossbench.mock_helper import (LinuxMockPlatform,
                                          RemoteLinuxMockPlatform)
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
    self.platform.expect_sh(
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

  # TODO: implement more mock tests
  def test_local_reverse_port_forward_invalid(self):
    pass

  def test_local_reverse_port_forward(self):
    pass

  def test_local_port_forward(self):
    pass


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
