# Web Power Benchmark

The "Web Power" benchmark measures the power consumption of various Web
workloads on Android devices.

Currently supported scenarios include:

- **Idle:** Static, fully loaded page. (Or as close to it as is possible, as
  pages can load arbitrary new content at any time.)
- **Scroll:** Actively scrolling up and down.
- **Page-Load:** The initial page-loading phase.
- **Media-Playback:** The steady-state of playing back video and audio.

The canonical sites used for power measurements are **Al Jazeera** (`ajnews`),
**CNN** (`cnn`), and **MSN** (`msn`). For the `media-playback` scenario, the
canonical site is **YouTube**.

Other sites (like `yahoo`) are supported by the benchmark but are considered
non-canonical; this can be because the site exhibits high variance between
measurements, because it's not representative of a large proportion of the Web,
or for any other reason.

A story consists of a combination of a scenario and a site (for example,
`idle-cnn` or `scroll-msn`). The site may be implied if only one is supported,
as is the case for media playback at the moment.

Power measurement is supported through various means. Currently, these include:

- **ODPM (On-Device Power Meter):** Hardware sensors built into many modern
  devices (like Pixel phones) that report precise power consumption for
  various system rails (e.g., CPU, GPU, Display).
- **External Dedicated Hardware:** Hardware like Kibble, paired with matching
  software like Bits, can be used for high-fidelity, external power profiling.

## Setup

### Getting the Code

The "Web Power" benchmark is part of the open source
[Crossbench](http://chromium.googlesource.com/) project. Instructions on how to
clone the repository and use the tool are available
[here](https://chromium.googlesource.com/crossbench). Note that these
instructions encourage you to use [depot_tools](https://chromium.googlesource.com/chromium/tools/depot_tools/+/HEAD/README.md).
You would do well to follow that guidance.

If you are a Googler, after fetching Crossbench, find the `.gclient` file.
It should contain a section named `"crossbench"`. Ensure it has the following
entry in its `"custom_vars"` section:

```
solutions = [
  {
    "name": "crossbench",
    "url": "https://chromium.googlesource.com/crossbench.git",
    "deps_file": "DEPS",
    "custom_deps": {},
    "custom_vars": {
      "checkout_crossbench_internal": True,
    },
  },
]
```

That is, make sure `"checkout_crossbench_internal"` is set to `True`.
After setting this for the first time, run `gclient sync` once to fetch
the crossbench-internal submodule.

### Obtaining Access to WPR Recordings

To ensure consistent results, the benchmark uses WPR (Web Page Replay) archives
stored in the `chrome-partner-loadline` cloud bucket. Request access to this
bucket [here](https://docs.google.com/forms/d/e/1FAIpQLSdCb1LYPlDEKuOd1lP21yZ9YDEvjq-9W0a5X9k7QxM_YjskzA/viewform).

After obtaining access, run the following command on your machine (this only
needs to be done once).

```bash
gcloud auth application-default login --disable-quota-project
```

If you run into any issues, please refer to the
[relevant section](https://chromium.googlesource.com/crossbench/+/refs/heads/main/config/benchmark/loadline2/#cloud-bucket-access)
of the LoadLine 2 guide. (The same bucket is used by both benchmarks.)

## Running the Benchmark

### Canonical Configuration Runs

To run a canonical power measurement that iterates over the 10 canonical stories
and runs each 5 times, with the recommended wait time in between, use:

```bash
./cb.py web-power --browser=adb:chrome
```

Canonical runs do not deviate from the default configuration. Any deviations
(like changing the number of repetitions or cooldown times) can significantly
affect the final scores, often by altering the device's thermal state.
Non-canonical runs are often useful, but for score-collection, it is imperative
to stick to the canonical configuration.

### Results

As with any Crossbench benchmark, results are available in the output directory
printed to the console at the end of the run.

The main metric of the Web Power benchmarks is power consumption. As mentioned
earlier, there are two ways to collect these - using ODPM or through dedicated
hardware.

We default to using ODPM metrics, which are collected using a Perfetto probe.
Users who have access to Bits may use that instead by specifying
`--bits-path=path/to/bits/binary`.

Normally these two collection methods are
mutually exclusive, as Perfetto trace collection impacts performance and
power, and we prefer to avoid such an unintended side-effect when possible.
However, users who wish to measure power in both ways at the same time can
explicitly add both `--bits-path` and
`--probe-config=config/benchmark/web_power/probe_config.hjson`.

#### ODPM

When using ODPM collection, Crossbench automatically captures Perfetto traces
containing power rail data. After the benchmark finishes, it automatically
processes these traces, extracts the relevant metrics, and outputs them in
two ways:

- Logs saved to the results directory (which is reported to `stdout`). This
  directory includes a Perfetto trace for each iteration (located in
  `runs/*/perfetto.trace.pb.gz`) that can be opened and visualized with
  [Perfetto UI](https://ui.perfetto.dev).
- A summary of the results printed directly to `stdout`.

Because power rails are highly specific to the device hardware, extracting
meaningful metrics requires device-specific Trace Processor SQL queries. The
benchmark maintains a mapping between device models (matched via regex) and
specific SQL query files (stored in the source code). The tool looks up the
device model, selects the appropriate SQL file, and auto-runs it against the
trace.

The queries associated with devices reveal information about them through their
power rails. As such, queries associated with unreleased devices should not be
committed to the open source project. It is possible to store these in such
private repositories as `crossbench-internal` (see
[Getting the Code](#getting-the-code)). Those who need to configure a different
private repository can come up with alternatives.

#### Kibble/Bits

When running the benchmark with external hardware using the `--bits-path` flag,
power metrics are collected from the hardware rather than from on-device
sensors. Bits captures high-fidelity power data throughout the run and outputs
it to a sub-directory of the dedicated Bits output directory. The name of this
sub-directory is controlled by the `--bits-out` flag. If this flag is omitted,
the sub-directory name defaults to the current timestamp in the format
`YYYYMMDD_HHMMSS`.

Additional supported Bits configuration includes:

- `--bits-device`: The device identifier passed to the Bits tool. Be advised
  that these are typically different from the ADB serial number of the device.
- `--bits-duration`: How long the Bits collection should run. By default, this
  spans from story-start to story-end (i.e., collecting data only during the
  actual workload, skipping initial browser setup and page navigation).
  This can normally be omitted.
- `--bits-port`: The service port number for the Bits tool. This can normally be
  omitted, in which case a port will be auto-assigned.

## Versioning

### Reading the Version

The version of Crossbench itself can be read using the `--version` flag.

```bash
./cb.py --version
```

The version of the benchmark can be read using the `--benchmark-version` flag.
Naturally, the benchmark itself should be specified; in our case, `web-power`.

```bash
./cb.py web-power --benchmark-version
```

You'd typically only care about the latter (Web Power version).

### Interpreting the Version String

The Web Power version follows the format A.B.C, where:

- **A** is expected to be incremented roughly every year, with `1` being the
  first entry, launched in 2026. Different values of `A` are expected to be
  associated with such different workloads and scores that they might sometimes
  be considered as distinct benchmarks.
- **B** is the major version within a given year. It will be incremented when
  significant changes are made that can affect the score.
- **C** is the minor version within a given `A.B` version. It is typically
  incremented following minor changes that have no significant impact on the
  scores themselves, but which might affect the ease with which the benchmarks
  are executed or scores are collected.
