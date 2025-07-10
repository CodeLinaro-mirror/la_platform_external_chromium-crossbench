# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import pathlib
from typing import Final
from unittest import mock, skipIf

import pyfakefs
from pyfakefs.fake_filesystem import OSType
from typing_extensions import override

from crossbench import path as pth
from crossbench.plt.android_adb import (Adb, AndroidAdbPlatform,
                                        AndroidDeviceInfo)
from crossbench.plt.arch import MachineArch
from crossbench.plt.port_manager import PortForwardException
from crossbench.plt.process_meminfo import ProcessMeminfo
from tests import test_helper
from tests.crossbench.mock_helper import WinMockPlatform
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

DUMPSYS_MEMINFO_TIMEOUT_OUTPUT = b'''
*** SERVICE 'meminfo' DUMP TIMEOUT (1ms) EXPIRED ***
'''

class BaseAndroidAdbMockPlatformTestCase(BasePosixMockPlatformTestCase):
  DEVICE_ID = "emulator-5554"
  platform: AndroidAdbPlatform

  @override
  def setUp(self) -> None:
    super().setUp()
    self.adb_setup()
    self.platform = AndroidAdbPlatform(
        self.mock_platform, self.DEVICE_ID, adb=self.adb)
    self.mock_platform_str(self.platform, "adb.mock_platform.arm64")

  def test_str(self):
    self.assertEqual(str(self.platform), "adb.mock_platform.arm64")

  def adb_setup(self):
    adb_patcher = mock.patch(
        "crossbench.plt.android_adb._find_adb_bin",
        return_value=pathlib.Path("adb"))
    adb_patcher.start()
    self.addCleanup(adb_patcher.stop)
    self.expect_startup_devices()
    self.adb = Adb(self.mock_platform, self.DEVICE_ID)

  def expect_startup_devices(self, devices: str = ADB_DEVICES_SAMPLE_OUTPUT):
    self.mock_platform.expect_sh(pathlib.Path("adb"), "start-server")
    self.mock_platform.expect_sh(
        pathlib.Path("adb"), "devices", "-l", result=devices)

  def expect_sh(self, *args, result=""):
    self.expect_adb("shell", *args, result=result)

  def expect_adb(self, *args, result=""):
    self.mock_platform.expect_sh(
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

class AndroidAdbOnWinMockPlatformTestCase(BaseAndroidAdbMockPlatformTestCase):
  __test__ = True

  @override
  def setUp(self) -> None:
    super().setUp()
    self.fs.os = OSType.WINDOWS

  @override
  def mock_platform_setup(self):
    self.mock_platform = WinMockPlatform()

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
    self.platform.mkdtemp("custom_prefix")

  def test_push(self):
    local_path = self.mock_platform.path("C:/foo/push.local.data")
    remote_path = self.platform.default_tmp_dir / "push.remote.data"
    self.assertIsInstance(local_path, pathlib.PureWindowsPath)
    self.fs.create_file(local_path, contents="some data")
    self.expect_adb("push", "C:\\foo\\push.local.data",
                    "/data/local/tmp/push.remote.data")
    self.platform.push(local_path, remote_path)

  def test_push_remote_win_path(self):
    local_path = self.mock_platform.path("C:/foo/push.local.data")
    remote_path = self.mock_platform.path("custom/push.remote.data")
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
      Adb(self.mock_platform, self.DEVICE_ID)

  def test_create_default_too_many_devices(self):
    self.expect_startup_devices()
    with self.assertRaises(ValueError) as cm:
      Adb(self.mock_platform)
    self.assertIn("too many", str(cm.exception).lower())

  def test_create_default_one_device(self):
    self.expect_startup_devices(ADB_DEVICE_SAMPLE_OUTPUT)
    adb = Adb(self.mock_platform)
    self.assertEqual(adb.serial_id, "emulator-5556")

  def test_create_default_one_device_invalid(self):
    self.expect_startup_devices(ADB_DEVICE_SAMPLE_OUTPUT)
    with self.assertRaises(ValueError) as cm:
      Adb(self.mock_platform, "")
    self.assertIn("invalid device identifier", str(cm.exception).lower())

  def test_create_by_name(self):
    self.expect_startup_devices(ADB_DEVICES_SAMPLE_OUTPUT)
    adb = Adb(self.mock_platform, "Nexus_7")
    self.assertEqual(adb.serial_id, "0a388e93")
    self.expect_startup_devices(ADB_DEVICES_SAMPLE_OUTPUT)
    adb = Adb(self.mock_platform, "Nexus 7")
    self.assertEqual(adb.serial_id, "0a388e93")

  def test_create_by_name_duplicate(self):
    self.expect_startup_devices(ADB_DEVICES_SAMPLE_OUTPUT)
    with self.assertRaises(ValueError) as cm:
      Adb(self.mock_platform, "Android_SDK_built_for_x86")
    self.assertIn("devices", str(cm.exception).lower())

  def test_basic_properties(self):
    self.assertTrue(self.platform.is_remote)
    self.assertEqual(self.platform.name, "android")
    self.assertIs(self.platform.host_platform, self.mock_platform)
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
    self.expect_sh("getprop ro.build.version.release", result="999")
    self.assertEqual(self.platform.version, "999")
    # Subsequent calls are cached.
    self.assertEqual(self.platform.version, "999")

  def test_device(self):
    self.expect_sh("getprop ro.product.model", result="Pixel 999")
    self.assertEqual(self.platform.device, "Pixel 999")
    # Subsequent calls are cached.
    self.assertEqual(self.platform.device, "Pixel 999")

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
      self.platform.search_binary(pathlib.Path(""))
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

  @skipIf(
      tuple(map(int, pyfakefs.__version__.split("."))) < (5, 5),
      "pth.AnyWindowsPath does not work correctly with older pyfakefs")
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
    with self.platform.ports.nested() as ports:
      port = ports.reverse_forward(0, 33300)
      self.assertEqual(port, 333)
      with self.platform.ports.nested() as ports:
        port = ports.reverse_forward(0, 33221)
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

  def test_meminfo_no_process(self):
    self.expect_sh(
        "dumpsys -T 10000 meminfo --proto --package com.android.chrome",
        result=b"")
    meminfo = self.platform.meminfo("com.android.chrome")
    self.assertEqual(len(meminfo), 0)

  def test_meminfo(self):
    self.expect_sh(
        "dumpsys -T 10000 meminfo --proto --package com.android.chrome",
        result=DUMPSYS_MEMINFO_OUTPUT)
    meminfo = self.platform.meminfo("com.android.chrome")
    self.assertEqual(len(meminfo), 4)

    self.assertEqual(
        meminfo, {
            "com.android.chrome:privileged_process0":
                ProcessMeminfo(20533, 37794, 186356, 203),
            "com.android.chrome:sandboxed_process0:org.chromium.content.app."
            "SandboxedProcessService0:0":
                ProcessMeminfo(20527, 49907, 184636, 245),
            "com.android.chrome:sandboxed_process0:org.chromium.content.app."
            "SandboxedProcessService0:1":
                ProcessMeminfo(20596, 30679, 156928, 244),
            "com.android.chrome":
                ProcessMeminfo(20438, 200986, 412436, 148)
        })

  def test_meminfo_timeout(self):
    self.expect_sh(
        "dumpsys -T 10000 meminfo --proto --package com.android.chrome",
        result=DUMPSYS_MEMINFO_TIMEOUT_OUTPUT)

    with self.assertRaises(TimeoutError):
      self.platform.meminfo("com.android.chrome")

if __name__ == "__main__":
  test_helper.run_pytest(__file__)
