# Copyright 2023 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import datetime as dt
import os
import pathlib
import sys
import tempfile
import unittest

from crossbench import compat, plt
from crossbench.plt.posix import PosixPlatform
from tests import test_helper


class NativePlatformTestCase(unittest.TestCase):

  def setUp(self):
    self.platform: plt.Platform = plt.PLATFORM

  def test_sleep(self):
    self.platform.sleep(0)
    self.platform.sleep(0.01)
    self.platform.sleep(dt.timedelta())
    self.platform.sleep(dt.timedelta(seconds=0.1))

  def test_cpu_details(self):
    details = self.platform.cpu_details()
    self.assertLess(0, details["physical cores"])

  def test_get_relative_cpu_speed(self):
    self.assertGreater(self.platform.get_relative_cpu_speed(), 0)

  def test_is_thermal_throttled(self):
    self.assertIsInstance(self.platform.is_thermal_throttled(), bool)

  def test_is_battery_powered(self):
    self.assertIsInstance(self.platform.is_battery_powered, bool)
    self.assertEqual(
        self.platform.is_battery_powered,
        plt.PLATFORM.is_battery_powered,
    )

  def test_cpu_usage(self):
    self.assertGreaterEqual(self.platform.cpu_usage(), 0)

  def test_system_details(self):
    self.assertIsNotNone(self.platform.system_details())

  def test_environ(self):
    env = self.platform.environ
    self.assertTrue(env)

  def test_which_none(self):
    with self.assertRaises(ValueError):
      self.platform.which("")

  def test_which_invalid_binary(self):
    with tempfile.TemporaryDirectory() as tmp_dirname:
      self.assertIsNone(self.platform.which(tmp_dirname))

  def test_search_binary_empty_path(self):
    with self.assertRaises(ValueError) as cm:
      self.platform.search_binary(pathlib.Path())
    self.assertIn("empty", str(cm.exception))
    with self.assertRaises(ValueError) as cm:
      self.platform.search_binary(pathlib.Path(""))
    self.assertIn("empty", str(cm.exception))

  def test_search_app_empty_path(self):
    with self.assertRaises(ValueError) as cm:
      self.platform.search_app(pathlib.Path())
    self.assertIn("empty", str(cm.exception))
    with self.assertRaises(ValueError) as cm:
      self.platform.search_app(pathlib.Path(""))
    self.assertIn("empty", str(cm.exception))

  def test_cat(self):
    with tempfile.TemporaryDirectory() as tmp_dirname:
      file = pathlib.Path(tmp_dirname) / "test.txt"
      with file.open("w") as f:
        f.write("a b c d e f 11")
      result = self.platform.cat(file)
      self.assertEqual(result, "a b c d e f 11")

  def test_mkdir(self):
    with tempfile.TemporaryDirectory() as tmp_dirname:
      path = pathlib.Path(tmp_dirname) / "foo" / "bar"
      self.assertFalse(self.platform.exists(path))
      self.platform.mkdir(path)
      self.assertTrue(path.is_dir())

  def test_rm_file(self):
    with tempfile.TemporaryDirectory() as tmp_dirname:
      path = pathlib.Path(tmp_dirname) / "foo.txt"
      path.touch()
      self.assertTrue(path.is_file())
      self.platform.rm(path)
      self.assertFalse(self.platform.exists(path))

  def test_rm_dir(self):
    with tempfile.TemporaryDirectory() as tmp_dirname:
      path = pathlib.Path(tmp_dirname) / "foo" / "bar"
      path.mkdir(parents=True, exist_ok=False)
      self.assertTrue(path.is_dir())
      with self.assertRaises(Exception):
        self.platform.rm(path.parent)
      self.platform.rm(path.parent, dir=True)
      self.assertFalse(self.platform.exists(path))
      self.assertFalse(path.parent.exists())

  def test_mkdtemp(self):
    result = self.platform.mkdtemp(prefix="a_custom_prefix")
    self.assertTrue(self.platform.is_dir(result))
    self.assertIn("a_custom_prefix", result.name)
    self.platform.rm(result, dir=True)
    self.assertFalse(self.platform.exists(result))

  def test_mkdtemp_dir(self):
    with tempfile.TemporaryDirectory() as tmp_dirname:
      tmp_dir = pathlib.Path(tmp_dirname)
      result = self.platform.mkdtemp(dir=tmp_dir)
      self.assertTrue(self.platform.is_dir(result))
      self.assertTrue(compat.is_relative_to(result, tmp_dir))
    self.assertFalse(self.platform.exists(result))

  def test_mktemp(self):
    result = self.platform.mktemp(prefix="a_custom_prefix")
    self.assertTrue(self.platform.is_file(result))
    self.assertIn("a_custom_prefix", result.name)
    self.platform.rm(result)
    self.assertFalse(self.platform.exists(result))

  def test_mktemp_dir(self):
    with tempfile.TemporaryDirectory() as tmp_dirname:
      tmp_dir = pathlib.Path(tmp_dirname)
      result = self.platform.mktemp(dir=tmp_dir)
      self.assertTrue(self.platform.is_file(result))
      self.assertTrue(compat.is_relative_to(result, tmp_dir))
    self.assertFalse(self.platform.exists(result))

  def test_exists(self):
    with tempfile.TemporaryDirectory() as tmp_dirname:
      tmp_dir = pathlib.Path(tmp_dirname)
      self.assertTrue(self.platform.exists(tmp_dir))
      self.assertFalse(self.platform.exists(tmp_dir / "foo"))

  def test_touch(self):
    with tempfile.TemporaryDirectory() as tmp_dirname:
      tmp_file = pathlib.Path(tmp_dirname) / "test.txt"
      self.assertFalse(tmp_file.exists())
      self.assertFalse(self.platform.exists(tmp_file))
      self.platform.touch(tmp_file)
      self.assertTrue(tmp_file.exists())
      self.assertTrue(self.platform.exists(tmp_file))
      self.assertEqual(tmp_file.stat().st_size, 0)

  def test_rename(self):
    with tempfile.TemporaryDirectory() as tmp_dirname:
      tmp_file = pathlib.Path(tmp_dirname) / "test.txt"
      tmp_file_renamed = tmp_file.with_name("test_renamed.txt")
      self.platform.touch(tmp_file)
      self.assertTrue(tmp_file.exists())
      self.assertFalse(tmp_file_renamed.exists())
      result = self.platform.rename(tmp_file, tmp_file_renamed)
      self.assertEqual(result, tmp_file_renamed)
      self.assertFalse(tmp_file.exists())
      self.assertTrue(tmp_file_renamed.exists())

  def test_default_tmp_dir(self):
    self.assertTrue(self.platform.is_dir(self.platform.default_tmp_dir))

  def test_NamedTemporaryFile(self):
    with self.platform.NamedTemporaryFile("custom_prefix") as path:
      self.assertIn("custom_prefix", str(path))
      self.assertTrue(self.platform.is_file(path))
      self.assertTrue(self.platform.exists(path))
    self.assertFalse(self.platform.exists(path))

  def test_copy(self):
    with tempfile.TemporaryDirectory() as tmp_dirname:
      src_file = pathlib.Path(tmp_dirname) / "src.txt"
      dst_file = pathlib.Path(tmp_dirname) / "dst.txt"
      with self.assertRaises(ValueError) as cm:
        self.assertFalse(self.platform.exists(src_file))
        self.platform.copy(src_file, dst_file)
      self.assertIn(str(src_file), str(cm.exception))
      self.assertFalse(self.platform.exists(src_file))
      self.assertFalse(self.platform.exists(dst_file))

      src_file.write_text("some data")
      self.assertTrue(self.platform.exists(src_file))
      self.platform.copy(src_file, dst_file)
      self.assertTrue(self.platform.exists(src_file))
      self.assertTrue(self.platform.exists(dst_file))
      self.assertEqual(self.platform.cat(src_file), "some data")
      self.assertEqual(self.platform.cat(dst_file), "some data")

  def test_home(self):
    self.assertEqual(self.platform.home(), pathlib.Path.home())

  def test_absolute_absolute(self):
    absolute_path = pathlib.Path("/foo")
    self.assertTrue(absolute_path.is_absolute())
    self.assertEqual(self.platform.absolute(absolute_path), absolute_path)

  def test_absolute_relative(self):
    if self.platform.is_remote:
      self.skipTest("Not supported yet on remote platforms.")
    relative_path = pathlib.Path("../../foo")
    self.assertFalse(relative_path.is_absolute())
    self.assertEqual(
        self.platform.absolute(relative_path), relative_path.absolute())

  def test_glob(self):
    if self.platform.is_remote:
      self.skipTest("Not supported yet on remote platforms.")
    with tempfile.TemporaryDirectory() as tmp_dirname:
      tmp_dir = pathlib.Path(tmp_dirname)
      self.assertFalse(list(self.platform.glob(tmp_dir, "*")))
      a = tmp_dir / "a"
      b = tmp_dir / "b"
      self.platform.touch(a)
      self.platform.touch(b)
      self.assertListEqual(sorted(self.platform.glob(tmp_dir, "*")), [a, b])

  def test_set_file_contents(self):
    if self.platform.is_remote:
      self.skipTest("Not supported yet on remote platforms.")
    with tempfile.TemporaryDirectory() as tmp_dirname:
      tmp_file = pathlib.Path(tmp_dirname) / "test.txt"
      self.assertFalse(self.platform.exists(tmp_file))
      self.platform.mkdir(tmp_file.parent)
      self.platform.touch(tmp_file)
      self.assertFalse(self.platform.cat(tmp_file))

      self.platform.set_file_contents(tmp_file, "custom data")
      self.assertTrue(self.platform.exists(tmp_file))
      self.assertEqual(self.platform.cat(tmp_file), "custom data")

  def test_set_file_contents_dir(self):
    if self.platform.is_remote:
      self.skipTest("Not supported yet on remote platforms.")
    with tempfile.TemporaryDirectory() as tmp_dirname:
      self.assertTrue(self.platform.is_dir(tmp_dirname))
      with self.assertRaises(Exception) as cm:
        self.platform.set_file_contents(tmp_dirname, "data")
      self.assertIn(str(tmp_dirname), str(cm.exception))

  def test_path_tests(self):
    with tempfile.TemporaryDirectory() as tmp_dirname:
      tmp_dir = pathlib.Path(tmp_dirname)
      self.assertTrue(self.platform.exists(tmp_dir))
      self.assertTrue(self.platform.is_dir(tmp_dir))
      self.assertFalse(self.platform.is_file(tmp_dir))

      foo_dir = tmp_dir / "foo"
      self.assertFalse(self.platform.exists(foo_dir))
      self.assertFalse(self.platform.is_dir(foo_dir))
      self.assertFalse(self.platform.is_file(foo_dir))
      self.platform.mkdir(foo_dir)
      self.assertTrue(self.platform.exists(foo_dir))
      self.assertTrue(self.platform.is_dir(foo_dir))
      self.assertFalse(self.platform.is_file(foo_dir))

      bar_file = tmp_dir / "bar.txt"
      self.assertFalse(self.platform.exists(bar_file))
      self.assertFalse(self.platform.is_dir(bar_file))
      self.assertFalse(self.platform.is_file(bar_file))
      self.platform.touch(bar_file)
      self.assertTrue(self.platform.exists(bar_file))
      self.assertFalse(self.platform.is_dir(bar_file))
      self.assertTrue(self.platform.is_file(bar_file))

  def test_has_display(self):
    self.assertIn(self.platform.has_display, (True, False))

  def test_processes(self):
    if self.platform.is_remote:
      self.skipTest("Not supported yet on remote platforms.")
    self.assertTrue(self.platform.processes())
    for process_info in self.platform.processes(["name"]):
      self.assertIn("name", process_info)

  def test_process_running(self):
    if self.platform.is_remote:
      self.skipTest("Not supported yet on remote platforms.")
    if test_helper.is_google_env():
      self.skipTest("Not supported yet in google environment.")
    self.assertFalse(self.platform.process_running([]))
    self.assertFalse(
        self.platform.process_running(["crossbench_invalid_test_bin"]))
    executable = pathlib.Path(sys.executable)
    self.assertTrue(self.platform.process_running([executable.name]))

  def test_process_info(self):
    if self.platform.is_remote:
      self.skipTest("Not supported yet on remote platforms.")
    if test_helper.is_google_env():
      self.skipTest("Not supported yet in google environment.")
    process_info = self.platform.process_info(os.getpid())
    self.assertIn("python", process_info["name"].lower())

  def test_process_children(self):
    if self.platform.is_remote:
      self.skipTest("Not supported yet on remote platforms.")
    process_info = self.platform.process_children(os.getpid())
    self.assertIsInstance(process_info, list)
    process_info = self.platform.process_children(os.getpid(), recursive=True)
    self.assertIsInstance(process_info, list)

  @unittest.skipIf(
      not plt.PLATFORM.which("python3"), reason="python3 not installed")
  def test_binary_lookup_override(self):
    test_binary = "crossbench-non-existing-test-binary"
    self.assertIsNone(self.platform.lookup_binary_override(test_binary))
    self.assertIsNone(self.platform.which(test_binary))
    # Use an arbitrary existing binary for testing.
    override_binary = self.platform.which("python3")
    self.assertTrue(override_binary)
    with self.platform.override_binary(test_binary, override_binary):
      self.assertEqual(self.platform.which(test_binary), override_binary)
      with self.platform.override_binary(test_binary, None):
        self.assertIsNone(self.platform.lookup_binary_override(test_binary))
        self.assertIsNone(self.platform.which(test_binary))
      self.assertEqual(self.platform.which(test_binary), override_binary)
    self.assertIsNone(self.platform.lookup_binary_override(test_binary))
    self.assertIsNone(self.platform.which(test_binary))


@unittest.skipIf(not plt.PLATFORM.is_posix, "Incompatible platform")
class PosixNativePlatformTestCase(NativePlatformTestCase):
  platform: PosixPlatform

  def setUp(self):
    super().setUp()
    assert isinstance(plt.PLATFORM, PosixPlatform)
    self.platform: PosixPlatform = plt.PLATFORM

  def test_sh(self):
    ls = self.platform.sh_stdout("ls")
    self.assertTrue(ls)
    lsa = self.platform.sh_stdout("ls", "-a")
    self.assertTrue(lsa)
    self.assertNotEqual(ls, lsa)

  def test_which(self):
    ls_bin = self.platform.which("ls")
    self.assertIsNotNone(ls_bin)
    bash_bin = self.platform.which("bash")
    self.assertIsNotNone(bash_bin)
    self.assertNotEqual(ls_bin, bash_bin)
    self.assertTrue(pathlib.Path(ls_bin).exists())
    self.assertTrue(pathlib.Path(bash_bin).exists())

  def test_system_details(self):
    details = self.platform.system_details()
    self.assertTrue(details)

  def test_search_binary(self):
    result_path = self.platform.search_binary(pathlib.Path("ls"))
    self.assertIsNotNone(result_path)
    self.assertIn("ls", result_path.parts)
    self.assertTrue(self.platform.exists(result_path))

  def test_search_binary_posix_lookup_override(self):
    path = pathlib.Path("ls")
    override = self.platform.which("cp")
    with self.platform.override_binary(path, override):
      result_path = self.platform.search_binary(path)
      self.assertEqual(result_path, override)
      self.assertTrue(self.platform.exists(result_path))

    result_path_2 = self.platform.search_binary(path)
    self.assertNotEqual(result_path_2, result_path)
    self.assertTrue(self.platform.exists(result_path_2))
    self.assertIsNone(self.platform.lookup_binary_override(path))

  def test_environ(self):
    env = self.platform.environ
    self.assertTrue(env)
    self.assertIn("PATH", env)
    self.assertTrue(list(env))

  def test_environ_set_property(self):
    env = self.platform.environ
    custom_key = f"CROSSBENCH_TEST_KEY_{len(env)}"
    self.assertNotIn(custom_key, env)
    with self.assertRaises(Exception):
      env[custom_key] = 1234
    env[custom_key] = "1234"
    self.assertEqual(env[custom_key], "1234")
    self.assertIn(custom_key, env)
    del env[custom_key]
    self.assertNotIn(custom_key, env)

  def test_app_version(self):
    if test_helper.is_google_env():
      self.skipTest("Not supported yet in google environment.")
    python_path = sys.executable
    with self.assertRaises(ValueError):
      self.platform.app_version("path/to/invalid/test/crossbench/bin")
    version = self.platform.app_version(python_path)
    self.assertTrue(version)

class MockRemotePosixPlatform(type(plt.PLATFORM)):

  @property
  def host_platform(self):
    return plt.PLATFORM

  def is_remote(self) -> bool:
    return True

  def local_path(self, path):
    # override to bypass is_local checks
    return pathlib.Path(path)

  def sh(self, *args, **kwargs):
    return plt.PLATFORM.sh(*args, **kwargs)

  def sh_stdout(self, *args, **kwargs):
    return plt.PLATFORM.sh_stdout(*args, **kwargs)


@unittest.skipIf(not plt.PLATFORM.is_posix, "Incompatible platform")
class MockRemotePosixPlatformTestCase(PosixNativePlatformTestCase):
  """All Posix operations should also work on a remote platform (e.g. via SSH).
  This test fakes this by temporarily changing the current PLATFORM's is_remote
  getter to return True"""

  def setUp(self):
    super().setUp()
    self.platform = MockRemotePosixPlatform()

  def test_is_remote(self):
    self.assertTrue(self.platform.is_remote)

  def tests_default_tmp_dir(self):
    self.assertEqual(self.platform.default_tmp_dir,
                     plt.PLATFORM.default_tmp_dir)

  def test_environ_set_property(self):
    raise self.skipTest("Not supported on remote platforms")

  def test_cpu_usage(self):
    raise self.skipTest("Not supported on remote platforms")


@unittest.skipIf(not plt.PLATFORM.is_macos, "Incompatible platform")
class MacOSNativePlatformTestCase(PosixNativePlatformTestCase):
  platform: plt.MacOSPlatform

  def setUp(self):
    super().setUp()
    assert isinstance(plt.PLATFORM, plt.MacOSPlatform)
    self.platform = plt.PLATFORM

  def test_search_app_binary_not_found(self):
    binary = self.platform.search_binary(pathlib.Path("Invalid App Name"))
    self.assertIsNone(binary)
    binary = self.platform.search_binary(pathlib.Path("Non-existent App.app"))
    self.assertIsNone(binary)

  def test_search_app_binary(self):
    binary = self.platform.search_binary(pathlib.Path("Safari.app"))
    self.assertIsNotNone(binary)
    self.assertTrue(self.platform.is_file(binary))
    # We should get the binary not the app bundle
    self.assertFalse(binary.suffix, ".app")
    self.assertEqual(binary.name, "Safari")

  def test_search_app_binary_override(self):
    override = pathlib.Path("/System/Applications/Calendar.app")
    with self.platform.override_binary("Safari.app", override):
      binary = self.platform.search_binary(pathlib.Path("Safari.app"))
      self.assertIsNotNone(binary)
      self.assertTrue(self.platform.is_file(binary))
      # We should get the binary not the app bundle
      self.assertFalse(binary.suffix, ".app")
    self.assertEqual(binary.name, "Calendar")

  def test_search_app_invalid(self):
    with self.assertRaises(ValueError):
      self.platform.search_app(pathlib.Path("Invalid App Name"))

  def test_search_app_none(self):
    self.assertIsNone(self.platform.search_app(pathlib.Path("No App.app")))

  def test_search_app(self):
    binary = self.platform.search_app(pathlib.Path("Safari.app"))
    self.assertIsNotNone(binary)
    self.assertTrue(self.platform.exists(binary))
    self.assertTrue(self.platform.is_dir(binary))

  def test_search_app_override(self):
    override = pathlib.Path("/System/Applications/Calendar.app")
    with self.platform.override_binary("Safari.app", override):
      binary = self.platform.search_app(pathlib.Path("Safari.app"))
      self.assertIsNotNone(binary)
      self.assertTrue(self.platform.exists(binary))
      self.assertTrue(self.platform.is_dir(binary))
      self.assertEqual(binary.name, "Calendar.app")

  def test_app_version_app(self):
    app = self.platform.search_app(pathlib.Path("Safari.app"))
    self.assertIsNotNone(app)
    self.assertTrue(app.is_dir())
    version = self.platform.app_version(app)
    self.assertRegex(version, r"[0-9]+\.[0-9]+")

  def test_app_version_app_binary(self):
    binary = self.platform.search_binary(pathlib.Path("Safari.app"))
    self.assertIsNotNone(binary)
    self.assertTrue(binary.is_file())
    version = self.platform.app_version(binary)
    self.assertRegex(version, r"[0-9]+\.[0-9]+")

  def test_app_version_binary(self):
    binary = pathlib.Path("/usr/bin/safaridriver")
    self.assertTrue(binary.is_file())
    version = self.platform.app_version(binary)
    self.assertRegex(version, r"[0-9]+\.[0-9]+")

  def test_name(self):
    self.assertEqual(self.platform.name, "macos")

  def test_version(self):
    self.assertTrue(self.platform.version)
    self.assertRegex(self.platform.version, r"[0-9]+\.[0-9]")

  def test_device(self):
    self.assertTrue(self.platform.device)
    self.assertRegex(self.platform.device, r"[a-zA-Z]+[0-9]+,[0-9]+")

  def test_cpu(self):
    self.assertTrue(self.platform.cpu)
    self.assertRegex(self.platform.cpu, r".* [0-9]+ cores")

  def test_foreground_process(self):
    self.assertTrue(self.platform.foreground_process())

  def test_is_macos(self):
    self.assertTrue(self.platform.is_macos)
    self.assertFalse(self.platform.is_linux)
    self.assertFalse(self.platform.is_win)
    self.assertFalse(self.platform.is_remote)

  def test_set_main_screen_brightness(self):
    prev_level = plt.PLATFORM.get_main_display_brightness()
    brightness_level = 32
    plt.PLATFORM.set_main_display_brightness(brightness_level)
    self.assertEqual(brightness_level,
                     plt.PLATFORM.get_main_display_brightness())
    plt.PLATFORM.set_main_display_brightness(prev_level)
    self.assertEqual(prev_level, plt.PLATFORM.get_main_display_brightness())

  def test_check_autobrightness(self):
    self.platform.check_autobrightness()

  def test_exec_apple_script(self):
    self.assertEqual(
        self.platform.exec_apple_script('copy "a value" to stdout').strip(),
        "a value")

  def test_exec_apple_script_args(self):
    result = self.platform.exec_apple_script("copy item 1 of argv to stdout",
                                             "a value", "b")
    self.assertEqual(result.strip(), "a value")
    result = self.platform.exec_apple_script("copy item 2 of argv to stdout",
                                             "a value", "b")
    self.assertEqual(result.strip(), "b")

  def test_exec_apple_script_invalid(self):
    with self.assertRaises(plt.SubprocessError):
      self.platform.exec_apple_script('something is not right 11')


@unittest.skipIf(not plt.PLATFORM.is_win, "Incompatible platform")
class WinNativePlatformTestCase(NativePlatformTestCase):
  platform: plt.WinPlatform

  def setUp(self):
    super().setUp()
    assert isinstance(plt.PLATFORM, plt.WinPlatform)
    self.platform = plt.PLATFORM

  def test_sh(self):
    ls = self.platform.sh_stdout("ls")
    self.assertTrue(ls)

  def test_search_binary(self):
    with self.assertRaises(ValueError):
      self.platform.search_binary(pathlib.Path("does not exist"))
    path = self.platform.search_binary(
        pathlib.Path("Windows NT/Accessories/wordpad.exe"))
    self.assertTrue(path and path.exists())

  def test_app_version(self):
    path = self.platform.search_binary(
        pathlib.Path("Windows NT/Accessories/wordpad.exe"))
    self.assertTrue(path and path.exists())
    version = self.platform.app_version(path)
    self.assertIsNotNone(version)

  def test_is_macos(self):
    self.assertFalse(self.platform.is_macos)
    self.assertFalse(self.platform.is_linux)
    self.assertTrue(self.platform.is_win)
    self.assertFalse(self.platform.is_remote)

  def test_has_display(self):
    self.assertIn(self.platform.has_display, (True, False))

  def test_version(self):
    self.assertTrue(self.platform.version)


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
