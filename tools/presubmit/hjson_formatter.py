# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import pathlib
import platform
import subprocess
from typing import Any


def GetNodeExecutable(input_api: Any) -> str:
  node_base: pathlib.Path = pathlib.Path(
      input_api.change.RepositoryRoot()) / "third_party" / "node"

  node_bin = ""

  if input_api.platform == "linux":
    node_bin = str(node_base / "linux" / "node-linux-x64" / "bin" / "node")
  if input_api.platform == "win32":
    node_bin = str(node_base / "win" / "node.exe")
  if input_api.platform == "darwin":
    if platform.machine() == "arm64":
      node_bin = str(node_base / "mac_arm64" / "node-darwin-arm64" / "bin" /
                     "node")
    else:
      node_bin = str(node_base / "mac" / "node-darwin-x64" / "bin" / "node")

  if not node_bin:
    raise NotImplementedError(f"{input_api.platform} {platform.machine()} "
                              "is not a supported platform.")

  return node_bin


def FormatHjsonFile(input_api: Any, hjson_file: pathlib.Path) -> str:
  node_bin = GetNodeExecutable(input_api)

  hjson_js_bin = str(
      pathlib.Path(input_api.change.RepositoryRoot()) / "third_party" /
      "hjson_js" / "bin" / "hjson")

  try:
    return subprocess.run([
        node_bin,
        hjson_js_bin,
        "-rt",
        "-sl",
        "-nocol",
        "-cond=0",
        "-quote=all",
        "-ml",
        str(hjson_file),
    ],
                          check=True,
                          capture_output=True).stdout.decode(encoding="utf-8")
  except subprocess.CalledProcessError as e:
    error = e.stderr.decode(encoding="utf-8")
    raise ValueError(f"Failed to parse hjson file: {error}") from e


def FormatHjsonFiles(
    input_api: Any,
    output_api: Any,
    modified_hjson_files: list[str],
) -> list[Any]:
  results: list[Any] = []
  for hjson_file in modified_hjson_files:
    full_hjson_path = pathlib.Path(
        input_api.change.RepositoryRoot()) / hjson_file

    try:
      formatted_contents: str = FormatHjsonFile(input_api, full_hjson_path)
    except ValueError as e:
      results.append(
          output_api.PresubmitPromptWarning(
              "Malformed hjson file:",
              items=[str(full_hjson_path)],
              long_text=str(e)))
      continue

    original_contents = input_api.ReadFile(str(full_hjson_path), "r")
    if original_contents != formatted_contents:
      full_hjson_path.write_text(formatted_contents)
      results.append(
          output_api.PresubmitPromptWarning(
              "Unformatted hjson file:",
              items=[str(full_hjson_path)],
              long_text="Please update your commit with the formatted file."))
  return results
