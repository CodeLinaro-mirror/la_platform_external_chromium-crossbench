# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import argparse
import pathlib
import textwrap
from typing import Final
from unittest import mock, skipIf

import pyfakefs
from pyfakefs.fake_filesystem import OSType
from typing_extensions import override

from crossbench import path as pth
from crossbench.plt.android_adb import Adb, AndroidAdbPlatform
from crossbench.plt.arch import MachineArch
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
    dumpsys_battery_output = textwrap.dedent("""
      AC powered: false
      USB powered: false
      Wireless powered: true
      Max charging current: 3000000
    """)
    self.expect_sh("dumpsys battery", result=dumpsys_battery_output)
    self.assertFalse(self.platform.is_battery_powered)
    dumpsys_battery_output = textwrap.dedent("""
      AC powered: false
      USB powered: false
      Wireless powered: false
      Max charging current: 3000000
    """)
    self.expect_sh("dumpsys battery", result=dumpsys_battery_output)
    self.assertTrue(self.platform.is_battery_powered)

  def test_display_details(self):
    dumpsys_window_output = textwrap.dedent("""
      WINDOW MANAGER DISPLAY CONTENTS (dumpsys window displays)
        Display: mDisplayId=0 (organized)
          init=1080x2400 480dpi mMinSizeOfResizeableTaskDp=220 cur=1080x2400 app=1080x2256 rng=1080x1008-2256x2184
          deferred=false mLayoutNeeded=false mTouchExcludeRegion=SkRegion((0,0,1080,2400))

        mLastOrientationSource=WindowedMagnification:0:31@1234567
     """)
    self.expect_sh("dumpsys window displays", result=dumpsys_window_output)
    result = self.platform.display_details()
    self.assertEqual(len(result), 1)
    self.assertDictEqual(result[0], {
        "resolution": (1080, 2400),
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
    self.assertDictEqual(
        self.adb.device_info, {
            "device": "generic_x86",
            "model": "Android_SDK_built_for_x86",
            "product": "sdk_google_phone_x86"
        })
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

  def test_port_forward(self):
    self.expect_adb("forward", "tcp:0", "tcp:33221", result="666")
    self.expect_adb("forward", "--remove", "tcp:666")
    port = self.platform.port_forward(0, 33221)
    self.assertEqual(port, 666)
    self.platform.stop_port_forward(port)

  def test_reverse_port_forward(self):
    self.expect_adb("reverse", "tcp:0", "tcp:33221", result="666")
    self.expect_adb("reverse", "--remove", "tcp:666")
    port = self.platform.reverse_port_forward(0, 33221)
    self.assertEqual(port, 666)
    self.platform.stop_reverse_port_forward(port)

  def test_port_forward_invalid(self):
    super().test_port_forward_invalid()
    with self.assertRaisesRegex(argparse.ArgumentTypeError, "remote_port"):
      self.platform.port_forward(1111, 0)

  def test_reverse_port_forward_invalid(self):
    super().test_reverse_port_forward_invalid()
    with self.assertRaisesRegex(argparse.ArgumentTypeError, "local_port"):
      self.platform.reverse_port_forward(1111, 0)

  def test_display_resolution(self):
    self.expect_sh(
        "dumpsys window displays",
        result="WINDOW MANAGER DISPLAY CONTENTS (dumpsys window displays)\n"
        "Display: mDisplayId=0 (organized)\n"
        "init=1366x768 136dpi mMinSizeOfResizeableTaskDp=220 "
        "cur=1366x768 app=1366x768 rng=768x768-1366x1366\n"
        "deferred=false mLayoutNeeded=false")
    [horizontal, vertical] = self.platform.display_resolution()
    self.assertEqual(horizontal, 1366)
    self.assertEqual(vertical, 768)

  def test_user_id(self):
    self.expect_sh("am get-current-user", result="10")
    self.assertEqual(self.platform.user_id(), 10)

  def test_meminfo_no_process(self):

    meminfo_result = '''
No process found for: com.android.chrome
'''

    self.expect_sh(
        "dumpsys meminfo --package com.android.chrome", result=meminfo_result)

    meminfo = self.platform.meminfo("com.android.chrome")

    self.assertEqual(len(meminfo), 0)

  def test_meminfo(self):
    meminfo_result = '''
Applications Memory Usage (in Kilobytes):
Uptime: 73731358 Realtime: 73731358

** MEMINFO in pid 14449 [com.android.chrome:privileged_process0] **
                   Pss  Private  Private     Swap      Rss     Heap     Heap     Heap
                 Total    Dirty    Clean    Dirty    Total     Size    Alloc     Free
                ------   ------   ------   ------   ------   ------   ------   ------
  Native Heap     3426     3368        0        0     7588    13372     6716     2587
  Dalvik Heap     1792     1316        0        0    10036     2479     1860      619
 Dalvik Other      561      556        0        0     1580                           
        Stack      476      476        0        0      484                           
       Ashmem     1378      104        0        0     4928                           
    Other dev        8        0        8        0      244                           
     .so mmap     1649      264       52        0    49544                           
    .jar mmap      309        0        0        0    30512                           
    .apk mmap    12495      948      396        0    50228                           
    .dex mmap      978        0        0        0     4628                           
    .oat mmap       84        0        0        0     8852                           
    .art mmap     1265     1016        0        0    32340                           
   Other mmap       42        4        8        0     1104                           
      Unknown     4573     4572        0        0     5732                           
        TOTAL    29036    12624      464        0   207800    15851     8576     3206
 
 App Summary
                       Pss(KB)                        Rss(KB)
                        ------                         ------
           Java Heap:     2332                          42376
         Native Heap:     3368                           7588
                Code:     1676                         143780
               Stack:      476                            484
            Graphics:        0                              0
       Private Other:     5236
              System:    15948
             Unknown:                                   13572
 
           TOTAL PSS:    29036            TOTAL RSS:   207800      TOTAL SWAP (KB):        0
 
 Objects
               Views:        0         ViewRootImpl:        0
         AppContexts:        4           Activities:        0
              Assets:       15        AssetManagers:        0
       Local Binders:        5        Proxy Binders:       39
       Parcel memory:        9         Parcel count:       15
    Death Recipients:        0             WebViews:        0
 
 Native Allocations
                         Count                       Total(kB)
                        ------                         ------
    Other (malloced):      317                             28
 Other (nonmalloced):       41                             33
 
 SQL
         MEMORY_USED:        0
  PAGECACHE_OVERFLOW:        0          MALLOC_SIZE:        0
 

** MEMINFO in pid 14438 [com.android.chrome:sandboxed_process0:org.chromium.content.app.SandboxedProcessService0:0] **
                   Pss  Private  Private     Swap      Rss     Heap     Heap     Heap
                 Total    Dirty    Clean    Dirty    Total     Size    Alloc     Free
                ------   ------   ------   ------   ------   ------   ------   ------
  Native Heap     1549     1464        0        0     6172    12236     5441     2406
  Dalvik Heap      509      420        0        0     8416     2356     1767      589
 Dalvik Other      418      380        0        0     1580                           
        Stack      301      296        0        0      320                           
       Ashmem     1331        0        0        0     5192                           
    Other dev        8        0        8        0      192                           
     .so mmap      177       68        0        0    22908                           
    .jar mmap      201        0        0        0    26456                           
    .apk mmap    10211      244       60        0    45128                           
    .ttf mmap     4948        0       72        0    10084                           
    .dex mmap      632        0        0        0     3760                           
    .oat mmap       56        0        0        0     7636                           
    .art mmap      560      292        0        0    31740                           
   Other mmap     1358        4        0        0     3980                           
      Unknown     5678     5648        0        0     6992                           
        TOTAL    27937     8816      140        0   180556    14592     7208     2995
 
 App Summary
                       Pss(KB)                        Rss(KB)
                        ------                         ------
           Java Heap:      712                          40156
         Native Heap:     1464                           6172
                Code:      460                         115988
               Stack:      296                            320
            Graphics:        0                              0
       Private Other:     6024
              System:    18981
             Unknown:                                   17920
 
           TOTAL PSS:    27937            TOTAL RSS:   180556      TOTAL SWAP (KB):        0
 
 Objects
               Views:        0         ViewRootImpl:        0
         AppContexts:        3           Activities:        0
              Assets:       15        AssetManagers:        0
       Local Binders:        2        Proxy Binders:        8
       Parcel memory:        3         Parcel count:       12
    Death Recipients:        0             WebViews:        0
 
 Native Allocations
                         Count                       Total(kB)
                        ------                         ------
    Other (malloced):      314                             28
 Other (nonmalloced):       19                             13
 
 SQL
         MEMORY_USED:        0
  PAGECACHE_OVERFLOW:        0          MALLOC_SIZE:        0
 

** MEMINFO in pid 14487 [com.android.chrome:sandboxed_process0:org.chromium.content.app.SandboxedProcessService0:1] **
                   Pss  Private  Private     Swap      Rss     Heap     Heap     Heap
                 Total    Dirty    Clean    Dirty    Total     Size    Alloc     Free
                ------   ------   ------   ------   ------   ------   ------   ------
  Native Heap     1552     1456        0        0     6156    12236     5432     2415
  Dalvik Heap      512      416        0        0     8412     2356     1767      589
 Dalvik Other      427      380        0        0     1580                           
        Stack      317      312        0        0      336                           
       Ashmem     2248      672        0        0     6376                           
    Other dev        8        0        8        0      192                           
     .so mmap      185       68        0        0    22992                           
    .jar mmap      201        0        0        0    26456                           
    .apk mmap    23069      276     9480        0    65640                           
    .ttf mmap     4936        0       60        0    10072                           
    .dex mmap      632        0        0        0     3760                           
    .oat mmap       56        0        0        0     7636                           
    .art mmap      564      292        0        0    31740                           
   Other mmap     1358        4        0        0     3980                           
      Unknown     8462     8432        0        0     9776                           
        TOTAL    44527    12308     9548        0   205104    14592     7199     3004
 
 App Summary
                       Pss(KB)                        Rss(KB)
                        ------                         ------
           Java Heap:      708                          40152
         Native Heap:     1456                           6156
                Code:     9900                         136572
               Stack:      312                            336
            Graphics:        0                              0
       Private Other:     9480
              System:    22671
             Unknown:                                   21888
 
           TOTAL PSS:    44527            TOTAL RSS:   205104      TOTAL SWAP (KB):        0
 
 Objects
               Views:        0         ViewRootImpl:        0
         AppContexts:        3           Activities:        0
              Assets:       15        AssetManagers:        0
       Local Binders:        2        Proxy Binders:        8
       Parcel memory:        2         Parcel count:       10
    Death Recipients:        0             WebViews:        0
 
 Native Allocations
                         Count                       Total(kB)
                        ------                         ------
    Other (malloced):      314                             28
 Other (nonmalloced):       19                             13
 
 SQL
         MEMORY_USED:        0
  PAGECACHE_OVERFLOW:        0          MALLOC_SIZE:        0
 

** MEMINFO in pid 14356 [com.android.chrome] **
                   Pss  Private  Private     Swap      Rss     Heap     Heap     Heap
                 Total    Dirty    Clean    Dirty    Total     Size    Alloc     Free
                ------   ------   ------   ------   ------   ------   ------   ------
  Native Heap    31503    31484        0        0    35436    40088    32627     3730
  Dalvik Heap    16950    16892        0        0    24612    29003    14502    14501
 Dalvik Other     4407     4276        0        0     5268                           
        Stack     1424     1424        0        0     1432                           
       Ashmem     2630     1020        0        0     6900                           
    Other dev      132        0      132        0      392                           
     .so mmap     2702      284      132        0    62044                           
    .jar mmap     1020        0        0        0    47792                           
    .apk mmap    45195     1116    21036        0   115256                           
    .ttf mmap      226        0       28        0     1072                           
    .dex mmap    13751        0    12668        0    17580                           
    .oat mmap      302        0        0        0    12856                           
    .art mmap     1939     1704        0        0    32516                           
   Other mmap    11124      444    10072        0    14096                           
      Unknown    35145    35144        0        0    36284                           
        TOTAL   168450    93788    44068        0   413536    69091    47129    18231
 
 App Summary
                       Pss(KB)                        Rss(KB)
                        ------                         ------
           Java Heap:    18596                          57128
         Native Heap:    31484                          35436
                Code:    35264                         256860
               Stack:     1424                           1432
            Graphics:        0                              0
       Private Other:    51088
              System:    30594
             Unknown:                                   62680
 
           TOTAL PSS:   168450            TOTAL RSS:   413536      TOTAL SWAP (KB):        500
 
 Objects
               Views:      355         ViewRootImpl:        1
         AppContexts:       13           Activities:        1
              Assets:       18        AssetManagers:        0
       Local Binders:      135        Proxy Binders:      104
       Parcel memory:       19         Parcel count:       78
    Death Recipients:       17             WebViews:        0
 
 Native Allocations
                         Count                       Total(kB)
                        ------                         ------
   Bitmap (malloced):       58                           6821
    Other (malloced):     2088                            198
 Other (nonmalloced):      282                            179
 
 SQL
         MEMORY_USED:        0
  PAGECACHE_OVERFLOW:        0          MALLOC_SIZE:        0
'''

    self.expect_sh(
        "dumpsys meminfo --package com.android.chrome", result=meminfo_result)

    meminfo = self.platform.meminfo("com.android.chrome")

    self.assertEqual(
        meminfo, {
            "com.android.chrome:privileged_process0":
                ProcessMeminfo(14449, 29036, 207800, 0),
            ("com.android.chrome:sandboxed_process0:org.chromium.content.app."
             "SandboxedProcessService0:0"):
                ProcessMeminfo(14438, 27937, 180556, 0),
            ("com.android.chrome:sandboxed_process0:org.chromium.content.app."
             "SandboxedProcessService0:1"):
                ProcessMeminfo(14487, 44527, 205104, 0),
            "com.android.chrome":
                ProcessMeminfo(14356, 168450, 413536, 500),
        })

if __name__ == "__main__":
  test_helper.run_pytest(__file__)
