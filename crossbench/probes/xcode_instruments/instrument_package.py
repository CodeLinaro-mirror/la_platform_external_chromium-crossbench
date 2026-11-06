# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Builds human-readable Instruments packages (.instrpkg) for `xctrace`.

An Instruments package source is an XML file declaring instruments, each of
which lists the built-in Instruments tables it records (by table name) and
their settings. Unlike a binary .tracetemplate, it is readable and reviewable.
`xcrun instrumentbuilder` builds it into an .instrdst, which `xctrace record`
records with `--package <instrdst> --instrument <title>`.
"""

from __future__ import annotations

import dataclasses
import hashlib
import plistlib
from typing import TYPE_CHECKING, Final, Self
from xml.etree import ElementTree

from crossbench import exception
from crossbench import path as pth
from crossbench.parse import PathParser
from crossbench.plt.bin import Binaries

if TYPE_CHECKING:
  from crossbench.plt.macos import MacOSPlatform
  from crossbench.plt.types import ListCmdArgs, TupleCmdArgs

# Apple's own Instruments packages (e.g. "CPU Counters"), relative to the
# active Xcode's Contents dir (the parent of `xcode-select -p`).
_APPLE_PACKAGES_DIR: Final[pth.LocalPath] = pth.LocalPath(
    "Applications/Instruments.app/Contents/Packages")
_APPLE_PACKAGE_SUFFIX: Final[str] = ".instrdst"
_CACHE_DIR_NAME: Final[str] = "instrument_packages"


@dataclasses.dataclass(frozen=True)
class InstrumentPackage:
  """A built Instruments package and the titles of its instruments."""
  path: pth.LocalPath
  instruments: tuple[str, ...]

  @property
  def record_args(self) -> TupleCmdArgs:
    """`xctrace record` arguments recording all of the package's
    instruments."""
    args: ListCmdArgs = ["--package", self.path]
    for instrument in self.instruments:
      args.extend(("--instrument", instrument))
    return tuple(args)

  @classmethod
  def parse_source(cls, value: object) -> pth.LocalPath:
    """Parses the path to an .instrpkg, failing early (at config parsing time)
    if it is not a valid package source declaring instruments."""
    source = PathParser.existing_file_path(value, "instrument")
    with exception.annotate_argparsing(
        f"Parsing Instruments package source {str(source)!r}"):
      cls.parse_instrument_titles(source)
    return source

  @classmethod
  def parse_instrument_titles(cls, source: pth.LocalPath) -> tuple[str, ...]:
    """Returns the titles of the instruments declared in an .instrpkg file."""
    titles = cls._texts(cls._parse_xml(source), "instrument/title")
    if not titles:
      raise ValueError(f"No instruments declared in {source}")
    return titles

  @classmethod
  def build(cls, host: MacOSPlatform, source: pth.LocalPath) -> Self:
    """Builds `source` with `xcrun instrumentbuilder`, or reuses the package
    cached for the same source and Xcode version."""
    instruments = cls.parse_instrument_titles(source)
    xcode_contents = cls._xcode_contents_dir(host)
    output = host.local_cache_dir(_CACHE_DIR_NAME) / cls._cache_name(
        host, source, xcode_contents)
    if not host.exists(output):
      cls._build_uncached(host, source, xcode_contents, output)
    return cls(output, instruments)

  @classmethod
  def _build_uncached(cls, host: MacOSPlatform, source: pth.LocalPath,
                      xcode_contents: pth.LocalPath,
                      output: pth.LocalPath) -> None:
    """Builds `source` into `output`.

    All of Apple's Instruments packages are linked so that the source can import
    any built-in table (e.g. counters-profile from "CPU Counters") without
    listing the packages that define them. The package is built next to
    `output` and then renamed, so an interrupted build is never reused.
    """
    apple_packages_dir = xcode_contents / _APPLE_PACKAGES_DIR
    link_args: ListCmdArgs = []
    for package in sorted(
        host.glob(apple_packages_dir, f"*{_APPLE_PACKAGE_SUFFIX}")):
      link_args.extend(("-l", package.name.removesuffix(_APPLE_PACKAGE_SUFFIX)))
    tmp_output = output.with_name(f"tmp-{output.name}")
    host.rm(tmp_output, dir=True, missing_ok=True)
    host.sh(
        Binaries.XCRUN.resolve_cached(host), "instrumentbuilder", "-i", source,
        "-o", tmp_output, "-L", apple_packages_dir, *link_args)
    host.rename(tmp_output, output)

  @classmethod
  def _xcode_contents_dir(cls, host: MacOSPlatform) -> pth.LocalPath:
    """The active Xcode's Contents dir, the parent of `xcode-select -p`."""
    developer_dir = host.sh_stdout(
        Binaries.XCODE_SELECT.resolve_cached(host), "-p").strip()
    return pth.LocalPath(developer_dir).parent

  @classmethod
  def _cache_name(cls, host: MacOSPlatform, source: pth.LocalPath,
                  xcode_contents: pth.LocalPath) -> str:
    """A cache name that changes with the source and the Xcode version."""
    version_plist = plistlib.loads(
        host.read_bytes(xcode_contents / "version.plist"))
    xcode_version = version_plist.get("ProductBuildVersion", "unknown")
    source_hash = hashlib.sha256(host.read_bytes(source)).hexdigest()[:16]
    return f"{source.stem}-{xcode_version}-{source_hash}{_APPLE_PACKAGE_SUFFIX}"

  @staticmethod
  def _parse_xml(source: pth.LocalPath) -> ElementTree.Element:
    # Trusted local package source checked into the repo or passed by the user.
    return ElementTree.parse(source).getroot()  # noqa: S314

  @staticmethod
  def _texts(root: ElementTree.Element, path: str) -> tuple[str, ...]:
    return tuple(elem.text.strip() for elem in root.findall(path) if elem.text)
