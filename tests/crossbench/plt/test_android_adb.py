# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import pathlib
from typing import Final
from unittest import mock

from pyfakefs.fake_filesystem import OSType
from typing_extensions import override

from crossbench import path as pth
from crossbench.helper.version import VersionParseError
from crossbench.plt.android_adb import Adb, AndroidAdbPlatform, \
    AndroidDeviceInfo, AndroidVersion
from crossbench.plt.arch import MachineArch
from crossbench.plt.port_manager import PortForwardException
from crossbench.plt.process_meminfo import ProcessMeminfo
from tests import test_helper
from tests.crossbench.mock_helper import ShResult, WinMockPlatform
from tests.crossbench.plt.helper import BasePosixMockPlatformTestCase

ADB_DEVICE_SAMPLE_OUTPUT = (
    "List of devices attached\n"
    "emulator-5556 device product:sdk_google_phone_x86_64 "
    "model:Android_SDK_built_for_x86_64 device:generic_x86_64\n")
ADB_DEVICES_SAMPLE_OUTPUT = (
    f"{ADB_DEVICE_SAMPLE_OUTPUT}"
    "emulator-5554 device product:sdk_google_phone_x86 "
    "model:Android_SDK_built_for_x86 device:generic_x86\n"
    "0a388e93      device usb:1-1 product:razor model:Nexus_7 device:flo\n")

DUMPSYS_DISPLAY_OUTPUT: Final[str] = """
  SensorObserver
    mIsProxActive=false
    mDozeStateByDisplay:
      0 -> false
BrightnessSynchronizer
  mLatestIntBrightness=43
  mLatestFloatBrightness=0.163
  mCurrentUpdate=null
"""


def load_pb(path: str):
  return (pth.LocalPath(__file__).parent / "pb" / path).read_bytes()


DUMPSYS_MEMINFO_OUTPUT = load_pb("dumpsys_meminfo.pb")
AC_POWERED_OUTPUT = load_pb("battery/ac_powered.pb")
BATTERY_POWERED_OUTPUT = load_pb("battery/battery_powered.pb")
DUMPSYS_WINDOW_DISPLAYS_OUTPUT = load_pb("display/1080p.pb")

DUMPSYS_MEMINFO_TIMEOUT_OUTPUT = b"""
*** SERVICE 'meminfo' DUMP TIMEOUT (1ms) EXPIRED ***
"""

DUMPSYS_MEMINFO_SYSTEM_OUTPUT = b"""
          0K: GL mtrack
          0K: Other mtrack

Total RAM: 7,698,860K (status normal)
 Free RAM: 1,234K (2,345K cached pss + 3,456K cached kernel + 4,567K free)
DMA-BUF:   817,715K (      152K mapped +   817,563K unmapped)
DMA-BUF Heaps:    24,844K
DMA-BUF Heaps pool:         0K
      GPU:   258,796K (  258,796K dmabuf +         0K private)
      Kernel CMA:         0K
 Used RAM: 3,528,301K (1,772,358K used pss + 1,755,943K kernel)
 Lost RAM:   362,207K
     ZRAM:   557,480K physical used for 1,723,064K in swap (11,284K total swap)
   Tuning: 192 (large 512), oom 322,560K, restore limit 107,520K (high-end-gfx)
"""

DUMPSYS_MEMINFO_SYSTEM_OUTPUT_NO_DMA_BUF = b"""
        800K: Ashmem
        324K: .ttf mmap
          0K: Cursor
          0K: Other mtrack

Total RAM: 3,486,196K (status moderate)
 Free RAM: 1,234K (2,345K cached pss + 3,456K cached kernel + 4,567K free)
      ION:   132,124K (  6,924K mapped +   125,200K unmapped +   0K pools)
      GPU:   194,788K
 Used RAM: 2,835,979K (2,170,795K used pss +   665,184K kernel)
 Lost RAM:   282,400K
     ZRAM:   203,732K physical used for 745,216K in swap (4,194,300K total swap)
   Tuning: 256 (large 512), oom 322,560K, restore limit 107,520K (high-end-gfx)
"""


class BaseAndroidAdbMockPlatformTestCase(BasePosixMockPlatformTestCase):
  DEVICE_ID = "emulator-5554"
  platform: AndroidAdbPlatform
  adb: Adb

  @override
  def setUp(self) -> None:
    self.adb_setup()
    super().setUp()

  @override
  def setup_platform(self):
    self.expect_startup_devices()
    self.adb = Adb(self.host_platform, self.DEVICE_ID)
    platform = AndroidAdbPlatform(
        self.host_platform, self.DEVICE_ID, adb=self.adb)
    self.mock_platform_str(platform, "adb.mock_platform.arm64")
    return platform

  def test_str(self):
    self.assertEqual(str(self.platform), "adb.mock_platform.arm64")

  def adb_setup(self):
    adb_patcher = mock.patch(
        "crossbench.plt.android_adb._find_adb_bin",
        return_value=pathlib.Path("adb"))
    adb_patcher.start()
    self.addCleanup(adb_patcher.stop)

  def expect_startup_devices(self, devices: str = ADB_DEVICES_SAMPLE_OUTPUT):
    if self.host_platform.is_macos:
      self.host_platform.expect_sh(
          "brew", "--prefix", result=ShResult(returncode=1))
    self.host_platform.expect_sh(pathlib.Path("adb"), "start-server")
    self.host_platform.expect_sh(
        pathlib.Path("adb"), "devices", "-l", result=devices)

  def expect_sh(self, *args, result=""):
    self.expect_adb("shell", *args, result=result)

  def expect_adb(self, *args, result=""):
    self.host_platform.expect_sh(
        pathlib.Path("adb"), "-s", self.DEVICE_ID, *args, result=result)

  def test_is_android(self):
    self.assertTrue(self.platform.is_android)

  def test_is_battery_powered(self):
    self.expect_sh("dumpsys battery --proto", result=AC_POWERED_OUTPUT)
    self.assertFalse(self.platform.is_battery_powered)

    self.expect_sh("dumpsys battery --proto", result=BATTERY_POWERED_OUTPUT)
    self.assertTrue(self.platform.is_battery_powered)

  def test_display_details(self):
    self.expect_sh(
        "dumpsys window displays --proto",
        result=DUMPSYS_WINDOW_DISPLAYS_OUTPUT)
    result = self.platform.display_details()
    self.assertEqual(len(result), 1)
    self.assertDictEqual(result[0], {
        "resolution": (1920, 1080),
        "refresh_rate": -1
    })

  def test_unique_name(self):
    self.expect_sh("getprop ro.product.cpu.abi", result="arm64-v8a")
    self.expect_sh("getprop ro.product.cpu.abi", result="arm64-v8a")
    platform_2 = AndroidAdbPlatform(
        self.host_platform, "SomeDeviceId", adb=self.adb)
    self.assertNotEqual(self.platform.unique_name, platform_2.unique_name)


class AndroidAdbOnWinMockPlatformTestCase(BaseAndroidAdbMockPlatformTestCase):
  __test__ = True

  @override
  def setUp(self) -> None:
    super().setUp()
    self.fs.os = OSType.WINDOWS

  @override
  def setup_host_platform(self):
    return WinMockPlatform()

  def test_host_platform(self):
    self.assertTrue(self.platform.host_platform.is_win)
    self.assertIsInstance(
        self.platform.host_path("foo/bar"), pathlib.PureWindowsPath)
    self.assertNotEqual(
        str(self.platform.host_path("foo/bar")),
        str(self.platform.path("foo/bar")))

  def test_mktemp(self):
    self.assertTrue(self.platform.default_tmp_dir.is_absolute())
    self.assertIsInstance(self.platform.default_tmp_dir, pathlib.PurePosixPath)
    self.expect_sh("mktemp -d /data/local/tmp/custom_prefix.XXXXXXXXXXX")
    self.platform.mkdtemp(prefix="custom_prefix.")

  def test_mktemp_prefix_and_suffix(self):
    # suffix need special handling on android.
    self.assertTrue(self.platform.default_tmp_dir.is_absolute())
    self.assertIsInstance(self.platform.default_tmp_dir, pathlib.PurePosixPath)
    self.expect_sh(
        "mktemp -d /data/local/tmp/custom_prefix.XXXXXXXXXXX",
        result="/data/local/tmp/custom_prefix.RANDOM")
    self.expect_sh(("mv /data/local/tmp/custom_prefix.RANDOM "
                    "/data/local/tmp/custom_prefix.RANDOM.custom_suffix"))
    self.platform.mkdtemp(".custom_suffix", "custom_prefix.")

  def test_mktemp_suffix(self):
    # suffix need special handling on android.
    self.assertTrue(self.platform.default_tmp_dir.is_absolute())
    self.assertIsInstance(self.platform.default_tmp_dir, pathlib.PurePosixPath)
    self.expect_sh(
        "mktemp -d /data/local/tmp/XXXXXXXXXXX",
        result="/data/local/tmp/RANDOM")
    self.expect_sh(
        "mv /data/local/tmp/RANDOM /data/local/tmp/RANDOM.custom_suffix")
    self.platform.mkdtemp(".custom_suffix")

  def test_push(self):
    local_path = self.host_platform.path("C:/foo/push.local.data")
    remote_path = self.platform.default_tmp_dir / "push.remote.data"
    self.assertIsInstance(local_path, pathlib.PureWindowsPath)
    self.fs.create_file(local_path, contents="some data")
    self.expect_adb("push", "C:\\foo\\push.local.data",
                    "/data/local/tmp/push.remote.data")
    self.platform.push(local_path, remote_path)

  def test_push_remote_win_path(self):
    local_path = self.host_platform.path("C:/foo/push.local.data")
    remote_path = self.platform.path("custom/push.remote.data")
    self.assertIsInstance(local_path, pathlib.PureWindowsPath)
    self.fs.create_file(local_path, contents="some data")
    self.expect_adb("push", "C:\\foo\\push.local.data",
                    "custom/push.remote.data")
    self.platform.push(local_path, remote_path)


class AndroidAdbMockPlatformTest(BaseAndroidAdbMockPlatformTestCase):
  __test__ = True

  def test_create_no_devices(self):
    self.expect_startup_devices("List of devices attached")
    with self.assertRaises(ValueError):
      Adb(self.host_platform, self.DEVICE_ID)

  def test_create_default_too_many_devices(self):
    self.expect_startup_devices()
    with self.assertRaises(ValueError) as cm:
      Adb(self.host_platform)
    self.assertIn("too many", str(cm.exception).lower())

  def test_create_default_one_device(self):
    self.expect_startup_devices(ADB_DEVICE_SAMPLE_OUTPUT)
    adb = Adb(self.host_platform)
    self.assertEqual(adb.serial_id, "emulator-5556")

  def test_create_default_one_device_invalid(self):
    self.expect_startup_devices(ADB_DEVICE_SAMPLE_OUTPUT)
    with self.assertRaises(ValueError) as cm:
      Adb(self.host_platform, "")
    self.assertIn("invalid device identifier", str(cm.exception).lower())

  def test_create_by_name(self):
    self.expect_startup_devices(ADB_DEVICES_SAMPLE_OUTPUT)
    adb = Adb(self.host_platform, "Nexus_7")
    self.assertEqual(adb.serial_id, "0a388e93")
    self.expect_startup_devices(ADB_DEVICES_SAMPLE_OUTPUT)
    adb = Adb(self.host_platform, "Nexus 7")
    self.assertEqual(adb.serial_id, "0a388e93")

  def test_create_by_name_duplicate(self):
    self.expect_startup_devices(ADB_DEVICES_SAMPLE_OUTPUT)
    with self.assertRaises(ValueError) as cm:
      Adb(self.host_platform, "Android_SDK_built_for_x86")
    self.assertIn("devices", str(cm.exception).lower())

  def test_basic_properties(self):
    self.assertTrue(self.platform.is_remote)
    self.assertEqual(self.platform.name, "android")
    self.assertIs(self.platform.host_platform, self.host_platform)
    self.assertEqual(self.platform.default_tmp_dir,
                     pathlib.PurePosixPath("/data/local/tmp/"))

  def test_adb_basic_properties(self):
    self.assertEqual(self.adb.serial_id, self.DEVICE_ID)
    self.assertEqual(
        self.adb.device_info,
        AndroidDeviceInfo(
            device_id=self.DEVICE_ID,
            name="generic_x86",
            model="Android_SDK_built_for_x86",
            product="sdk_google_phone_x86"))
    self.assertIn(self.DEVICE_ID, str(self.adb))

  def test_has_root(self):
    self.expect_sh("id", result="uid=2000(shell) gid=2000(shell)")
    self.assertFalse(self.adb.has_root())
    self.expect_sh("id", result="uid=0(root)n gid=0(root)")
    self.assertTrue(self.adb.has_root())

  def test_version(self):
    version_str = "13 (Tiramisu)"
    self.expect_sh("getprop ro.build.description", result=version_str)
    version = self.platform.version
    self.assertEqual(version.parts, (13,))
    self.assertEqual(version.version_str, version_str)
    self.assertIs(version, self.platform.version)

  def test_version_long(self):
    version_str = "oriole-user 13 TQ3A.230805.001 10452339 release-keys"
    self.expect_sh("getprop ro.build.description", result=version_str)
    version = self.platform.version
    self.assertEqual(version.parts, (13,))
    self.assertEqual(version.version_str, version_str)
    self.assertIs(version, self.platform.version)

  def test_device(self):
    self.expect_sh("getprop ro.product.model", result="Pixel 999")
    self.assertEqual(self.platform.model, "Pixel 999")
    # Subsequent calls are cached.
    self.assertEqual(self.platform.model, "Pixel 999")

  def test_cpu(self):
    self.expect_sh("getprop dalvik.vm.isa.arm.variant", result="cortex-a999")
    self.expect_sh("getprop ro.board.platform", result="msmnile")
    cpu_info = "processor       : 0\nprocessor       : 1"
    self.expect_sh(
        "grep -E 'processor|core id|physical id' /proc/cpuinfo",
        result=cpu_info)
    self.assertEqual(self.platform.cpu, "cortex-a999 msmnile 2 cores")
    # Subsequent calls are cached.
    self.assertEqual(self.platform.cpu, "cortex-a999 msmnile 2 cores")

  def test_cpu_detailed(self):
    self.expect_sh("getprop dalvik.vm.isa.arm.variant", result="cortex-a999")
    self.expect_sh("getprop ro.board.platform", result="msmnile")
    cpu_info = "processor       : 0\nprocessor       : 1"
    self.expect_sh(
        "grep -E 'processor|core id|physical id' /proc/cpuinfo",
        result=cpu_info)
    self.assertEqual(self.platform.cpu, "cortex-a999 msmnile 2 cores")
    # Subsequent calls are cached.
    self.assertEqual(self.platform.cpu, "cortex-a999 msmnile 2 cores")

  def test_adb(self):
    self.assertIs(self.platform.adb, self.adb)

  def test_machine_unknown(self):
    self.expect_sh("getprop ro.product.cpu.abi", result="arm37-XXX")
    with self.assertRaises(ValueError) as cm:
      self.assertEqual(self.platform.machine, MachineArch.ARM_64)
    self.assertIn("arm37-XXX", str(cm.exception))

  def test_machine_arm64(self):
    self.expect_sh("getprop ro.product.cpu.abi", result="arm64-v8a")
    self.assertEqual(self.platform.machine, MachineArch.ARM_64)
    # Subsequent calls are cached.
    self.assertEqual(self.platform.machine, MachineArch.ARM_64)

  def test_machine_arm32(self):
    self.expect_sh("getprop ro.product.cpu.abi", result="armeabi-v7a")
    self.assertEqual(self.platform.machine, MachineArch.ARM_32)
    # Subsequent calls are cached.
    self.assertEqual(self.platform.machine, MachineArch.ARM_32)

  def test_app_path_to_package_invalid_path(self):
    path = pathlib.Path("path/to/app.bin")
    with self.assertRaises(ValueError) as cm:
      self.platform.app_path_to_package(path)
    self.assertIn(str(self.platform.path(path)), str(cm.exception))

  def test_app_path_to_package_not_installed(self):
    with self.assertRaises(ValueError) as cm:
      self.expect_sh(
          "cmd package list packages",
          result=("package:com.google.android.wifi.resources\n"
                  "package:com.google.android.GoogleCamera"))
      self.platform.app_path_to_package(pathlib.Path("com.custom.app"))
    self.assertIn("com.custom.app", str(cm.exception))
    self.assertIn("not installed", str(cm.exception))

  def test_app_path_to_package(self):
    path = pathlib.Path("com.custom.app")
    self.expect_sh(
        "cmd package list packages",
        result=("package:com.google.android.wifi.resources\n"
                "package:com.custom.app"))
    self.assertEqual(self.platform.app_path_to_package(path), "com.custom.app")

  def test_app_version(self):
    path = pathlib.Path("com.custom.app")
    self.expect_sh("cmd package list packages", result="package:com.custom.app")
    self.expect_sh("dumpsys package com.custom.app", result="versionName=9.999")
    self.assertEqual(self.platform.app_version(path), "9.999")

  def test_app_version_unknown(self):
    path = pathlib.Path("com.custom.app")
    self.expect_sh("cmd package list packages", result="package:com.custom.app")
    self.expect_sh("dumpsys package com.custom.app", result="something")
    with self.assertRaises(ValueError) as cm:
      self.platform.app_version(path)
    self.assertIn("something", str(cm.exception))
    self.assertIn("com.custom.app", str(cm.exception))

  def test_get_relative_cpu_speed(self):
    self.assertGreater(self.platform.get_relative_cpu_speed(), 0)

  def test_check_autobrightness(self):
    self.assertTrue(self.platform.check_autobrightness())

  def get_main_display_brightness(self):
    display_info = ("BrightnessSynchronizer\n"
                    "mLatestFloatBrightness=0.5\n"
                    "mLatestIntBrightness=128\n"
                    "mPendingUpdate=null")
    self.expect_sh("dumpsys", "display", result=display_info)
    self.assertEqual(self.platform.get_main_display_brightness(), 50)
    # Values are not cached
    display_info = ("BrightnessSynchronizer\n"
                    "mLatestFloatBrightness=1.0\n"
                    "mLatestIntBrightness=255\n"
                    "mPendingUpdate=null")
    self.expect_sh("dumpsys", "display", result=display_info)
    self.assertEqual(self.platform.get_main_display_brightness(), 100)

  def test_search_binary_empty_path(self):
    with self.assertRaises(ValueError) as cm:
      self.platform.search_binary(pathlib.Path())
    self.assertIn("empty path", str(cm.exception))
    with self.assertRaises(ValueError) as cm:
      self.platform.search_binary("")
    self.assertIn("empty path", str(cm.exception))

  def test_search_binary(self):
    ls_path = self.platform.path("/system/bin/ls")
    self.expect_sh("which ls", result=str(ls_path))
    self.expect_sh(f"'[' -e {ls_path} ']'", result="")
    path = self.platform.search_binary("ls")
    self.assertEqual(str(path), str(ls_path))

  def test_binary_lookup_override(self):
    # Overriding the default test for android.
    ls_path = self.platform.path("ls")
    override_path = self.platform.path("/root/sbin/ls")
    # override_binary checks if the result binary exists.
    self.expect_sh(f"which {override_path}", result=str(override_path))
    self.expect_sh(f"'[' -e {override_path} ']'", result="")
    with self.platform.override_binary(ls_path, override_path):
      path = self.platform.search_binary("ls")
      self.assertEqual(path, override_path)

  def test_search_binary_app_package_non(self):
    self.expect_sh("which com.google.chrome", result="")
    self.expect_sh("cmd package list packages", result="")
    path = self.platform.search_binary("com.google.chrome")
    self.assertIsNone(path)

    self.expect_sh("which com.google.chrome", result="")
    self.expect_sh(
        "cmd package list packages", result="package:com.google.chrome")
    path = self.platform.search_binary("com.google.chrome")
    self.assertEqual(path, pathlib.PurePosixPath("com.google.chrome"))

  def test_search_binary_app_package_lookup_override(self):
    chrome_package = self.platform.path("com.google.chrome")
    chrome_dev_package = self.platform.path("com.chrome.dev")
    self.expect_sh(f"which {chrome_dev_package}", result="")
    self.expect_sh("cmd package list packages", result="package:com.chrome.dev")
    with self.platform.override_binary(chrome_package, chrome_dev_package):
      path = self.platform.search_binary(chrome_package)
      self.assertEqual(chrome_dev_package, path)

  def test_override_binary_non_existing_package(self):
    chrome_package = self.platform.path("com.google.chrome")
    chrome_dev_package = self.platform.path("com.chrome.dev")
    self.expect_sh(f"which {chrome_dev_package}", result="")
    self.expect_sh("cmd package list packages", result="")
    with self.assertRaises(ValueError) as cm:
      with self.platform.override_binary(chrome_package, chrome_dev_package):
        pass
    self.assertIn(str(chrome_package), str(cm.exception))
    self.assertIn(str(chrome_dev_package), str(cm.exception))

  def test_home(self):
    # not implemented yet
    with self.assertRaises(RuntimeError):
      self.platform.home()

  def test_get_main_display_brightness(self):
    self.expect_sh("dumpsys display", result=DUMPSYS_DISPLAY_OUTPUT)
    brightness = self.platform.get_main_display_brightness()
    self.assertEqual(brightness, 16)

  def test_iterdir(self):
    self.expect_sh("'[' -d parent_dir/child_dir ']'")
    self.expect_sh("ls -1 parent_dir/child_dir", result="file1\nfile2\n")

    self.assertSetEqual(
        set(self.platform.iterdir(pth.AnyWindowsPath("parent_dir\\child_dir"))),
        {
            pth.AnyPosixPath("parent_dir/child_dir/file1"),
            pth.AnyPosixPath("parent_dir/child_dir/file2")
        })

  def test_cat_file(self):
    self.expect_sh("cat path/to/a/file")
    self.platform.cat(self.platform.path("path/to/a/file"))
    self.expect_sh("cat 'path/with a space/to/a/file'")
    self.platform.cat(self.platform.path("path/with a space/to/a/file"))

  def test_sh_shell_invalid(self):
    with self.assertRaisesRegex(ValueError, "shell=True"):
      self.platform.sh_stdout("ls", "folder with space", shell=True)

  def test_sh_shell(self):
    self.expect_sh("ls sdcard", result="FILE1\nFILE2\n")
    self.assertEqual(self.platform.sh_stdout("ls", "sdcard"), "FILE1\nFILE2\n")

    self.expect_sh("ls 'folder with space'", result="FOLDER\n")
    self.assertEqual(
        self.platform.sh_stdout("ls", "folder with space"), "FOLDER\n")

    self.expect_sh("'ls foo && ls bar'", result="FILE1\nFILE2\n")
    self.assertEqual(
        self.platform.sh_stdout("ls foo && ls bar"), "FILE1\nFILE2\n")

    self.expect_sh("ls foo && ls bar", result="FILE1\nFILE2\n")
    self.assertEqual(
        self.platform.sh_stdout("ls foo && ls bar", shell=True),
        "FILE1\nFILE2\n")

    self.expect_sh("ls foo '&&' ls bar", result="FILE1\nFILE2\n")
    self.assertEqual(
        self.platform.sh_stdout("ls", "foo", "&&", "ls", "bar"),
        "FILE1\nFILE2\n")

  def test_port_forward_default(self):
    # Closing the default port-manager happens in the atexit handler.
    self.expect_adb("forward", "tcp:0", "tcp:33221", result="666")
    self.platform.ports.forward(0, 33221)
    self.expect_adb("forward", "--remove", "tcp:666")
    self.platform.ports.stop_forward(666)

  def test_port_forward(self):
    self.expect_adb("forward", "tcp:0", "tcp:33221", result="666")
    self.expect_adb("forward", "--remove", "tcp:666")
    with self.platform.ports.nested() as ports:
      port = ports.forward(0, 33221)
      self.assertEqual(port, 666)
      # Cannot forward the same ports in a nested scope.
      with self.platform.ports.nested() as ports_2:
        with self.assertRaises(PortForwardException):
          ports_2.forward(666, 33221)
      ports.stop_forward(port)
      with self.assertRaises(PortForwardException):
        ports.stop_forward(port)

  def test_port_forward_auto_close(self):
    self.expect_adb("forward", "tcp:0", "tcp:33221", result="666")
    self.expect_adb("forward", "--remove", "tcp:666")
    with self.platform.ports.nested() as ports:
      port = ports.forward(0, 33221)
      self.assertEqual(port, 666)

  def test_reverse_port_forward_default(self):
    self.expect_adb("reverse", "tcp:0", "tcp:33221", result="666")
    self.platform.ports.reverse_forward(0, 33221)
    self.expect_adb("reverse", "--remove", "tcp:666")
    self.platform.ports.stop_reverse_forward(666)

  def test_reverse_port_forward(self):
    with self.platform.ports.nested() as ports:
      self.expect_adb("reverse", "tcp:0", "tcp:33221", result="666")
      self.expect_adb("reverse", "--remove", "tcp:666")
      port = ports.reverse_forward(0, 33221)
      self.assertEqual(port, 666)
      # Cannot forward the same ports in a nested scope.
      with self.platform.ports.nested() as ports_2:
        with self.assertRaises(PortForwardException):
          ports_2.reverse_forward(666, 33221)
      ports.stop_reverse_forward(port)
      with self.assertRaises(PortForwardException):
        ports.stop_reverse_forward(port)

  def test_reverse_port_forward_nested_auto_close(self):
    self.expect_adb("reverse", "tcp:0", "tcp:33300", result="333")
    self.expect_adb("reverse", "tcp:0", "tcp:33221", result="666")
    self.expect_adb("reverse", "--remove", "tcp:666")
    self.expect_adb("reverse", "--remove", "tcp:333")
    with self.platform.ports.nested() as ports_1:
      port = ports_1.reverse_forward(0, 33300)
      self.assertEqual(port, 333)
      with self.platform.ports.nested() as ports_2:
        port = ports_2.reverse_forward(0, 33221)
        self.assertEqual(port, 666)

  def test_reverse_port_forward_auto_close(self):
    self.expect_adb("reverse", "tcp:0", "tcp:33221", result="666")
    self.expect_adb("reverse", "--remove", "tcp:666")
    with self.platform.ports.nested() as ports:
      port = ports.reverse_forward(0, 33221)
      self.assertEqual(port, 666)

  def test_port_forward_invalid_adb(self):
    with self.platform.ports.nested() as ports:
      with self.assertRaisesRegex(argparse.ArgumentTypeError, "remote_port"):
        ports.forward(1111, 0)

  def test_reverse_port_forward_invalid_adb(self):
    with self.platform.ports.nested() as ports:
      with self.assertRaisesRegex(argparse.ArgumentTypeError, "local_port"):
        ports.reverse_forward(1111, 0)

  def test_display_resolution(self):
    self.expect_sh(
        "dumpsys window displays --proto",
        result=DUMPSYS_WINDOW_DISPLAYS_OUTPUT)
    [horizontal, vertical] = self.platform.display_resolution()
    self.assertEqual(horizontal, 1920)
    self.assertEqual(vertical, 1080)

  def test_user_id(self):
    self.expect_sh("am get-current-user", result="10")
    self.assertEqual(self.platform.user_id(), 10)

  def test_process_meminfo_no_process(self):
    self.expect_sh(
        "dumpsys -T 10000 meminfo --proto --package com.android.chrome",
        result=b"")
    meminfo = self.platform.process_meminfo("com.android.chrome")
    self.assertEqual(len(meminfo), 0)

  def test_process_meminfo(self):
    self.expect_sh(
        "dumpsys -T 10000 meminfo --proto --package com.android.chrome",
        result=DUMPSYS_MEMINFO_OUTPUT)
    meminfo = self.platform.process_meminfo("com.android.chrome")
    self.assertEqual(len(meminfo), 4)

    privileged_process = "com.android.chrome:privileged_process0"
    sandbox_prefix = ("com.android.chrome:sandboxed_process0:org.chromium."
                      "content.app.SandboxedProcessService0:")
    self.assertEqual(meminfo, [
        ProcessMeminfo(20533, privileged_process, 37794, 186356, 203),
        ProcessMeminfo(20527, f"{sandbox_prefix}0", 49907, 184636, 245),
        ProcessMeminfo(20596, f"{sandbox_prefix}1", 30679, 156928, 244),
        ProcessMeminfo(20438, "com.android.chrome", 200986, 412436, 148)
    ])

  def test_process_meminfo_timeout(self):
    self.expect_sh(
        "dumpsys -T 10000 meminfo --proto --package com.android.chrome",
        result=DUMPSYS_MEMINFO_TIMEOUT_OUTPUT)

    with self.assertRaises(TimeoutError):
      self.platform.process_meminfo("com.android.chrome")

  def test_system_meminfo(self):
    self.expect_sh(
        "dumpsys -T 10000 meminfo", result=DUMPSYS_MEMINFO_SYSTEM_OUTPUT)
    meminfo = self.platform.system_meminfo()
    self.assertDictEqual(
        meminfo, {
            "total_ram_kb": 7698860.0,
            "cached_pss_kb": 2345.0,
            "cached_kernel_kb": 3456.0,
            "free_kb": 4567.0,
            "dma_buf_kb": 817715.0,
            "dma_buf_mapped_kb": 152.0,
            "dma_buf_unmapped_kb": 817563.0,
        })

  def test_system_meminfo_no_dma_buf(self):
    self.expect_sh(
        "dumpsys -T 10000 meminfo",
        result=DUMPSYS_MEMINFO_SYSTEM_OUTPUT_NO_DMA_BUF)
    meminfo = self.platform.system_meminfo()
    self.assertDictEqual(
        meminfo, {
            "total_ram_kb": 3486196.0,
            "cached_pss_kb": 2345.0,
            "cached_kernel_kb": 3456.0,
            "free_kb": 4567.0,
        })

  def test_system_meminfo_timeout(self):
    self.expect_sh(
        "dumpsys -T 10000 meminfo", result=DUMPSYS_MEMINFO_TIMEOUT_OUTPUT)

    with self.assertRaises(TimeoutError):
      self.platform.system_meminfo()

  def test_doze(self):
    self.expect_sh("dumpsys deviceidle force-idle")
    self.platform.doze()

  def test_exit_doze(self):
    self.expect_sh("dumpsys deviceidle unforce")
    self.expect_sh("dumpsys battery reset")
    self.platform.exit_doze()

  def test_lock_screen(self):
    self.expect_sh("input keyevent KEYCODE_POWER")
    self.platform.lock_screen()

  def test_unlock_screen(self):
    self.expect_sh("input keyevent KEYCODE_WAKEUP")
    self.expect_sh("input keyevent KEYCODE_MENU")
    self.platform.unlock_screen()

  def test_platform_version_cls(self):
    version = AndroidVersion.parse("13 (Tiramisu)")
    self.assertEqual(version.parts, (13,))
    self.assertEqual(version.version_str, "13 (Tiramisu)")
    with self.assertRaises(VersionParseError):
      AndroidVersion.parse("foo")


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
