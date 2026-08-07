# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

from unittest import mock

from typing_extensions import override

from crossbench import path as pth
from crossbench.uploader.gcs import GoogleCloudStorageUploader
from tests import test_helper
from tests.crossbench.base import BaseCrossbenchTestCase


class GoogleCloudStorageUploaderTestCase(BaseCrossbenchTestCase):

  @override
  def setUp(self) -> None:
    super().setUp()
    self.out_dir.mkdir()

  def test_invalid_url_scheme(self) -> None:
    with self.assertRaises(AssertionError):
      GoogleCloudStorageUploader("https://storage.googleapis.com/my-bucket/")

  def test_upload_single_file(self) -> None:
    uploader = GoogleCloudStorageUploader("gs://my-bucket/test/")
    test_file = self.out_dir / "test_uuid.gz"
    test_file.write_text("data", encoding="utf-8")

    with mock.patch("crossbench.plt.PLATFORM.which") as mock_which, \
         mock.patch("crossbench.plt.PLATFORM.sh") as mock_sh:
      mock_which.return_value = pth.LocalPath("/usr/bin/gcloud")
      mock_sh.return_value.returncode = 0
      url = uploader.upload(test_file)
      self.assertEqual(url, "gs://my-bucket/test/test_uuid.gz")
      mock_which.assert_called_once_with("gcloud")
      mock_sh.assert_called_once_with(
          pth.LocalPath("/usr/bin/gcloud"),
          "storage",
          "cp",
          test_file,
          "gs://my-bucket/test/test_uuid.gz",
          capture_output=True,
          check=False,
      )

  def test_upload_missing_gcloud(self) -> None:
    uploader = GoogleCloudStorageUploader("gs://my-bucket/test/")
    test_file = self.out_dir / "test_uuid.gz"

    with mock.patch("crossbench.plt.PLATFORM.which", return_value=None):
      with self.assertRaises(RuntimeError) as cm:
        uploader.upload(test_file)
      self.assertIn("gcloud", str(cm.exception))

  def test_upload_gcloud_error(self) -> None:
    uploader = GoogleCloudStorageUploader("gs://my-bucket/test/")
    test_file = self.out_dir / "test_uuid.gz"

    with mock.patch("crossbench.plt.PLATFORM.which") as mock_which, \
         mock.patch("crossbench.plt.PLATFORM.sh") as mock_sh:
      mock_which.return_value = pth.LocalPath("/usr/bin/gcloud")
      mock_sh.return_value.returncode = 1
      mock_sh.return_value.stderr = "Permission denied"
      with self.assertRaises(RuntimeError) as cm:
        uploader.upload(test_file)
      self.assertIn("Permission denied", str(cm.exception))


if __name__ == "__main__":
  test_helper.run_pytest(__file__)
