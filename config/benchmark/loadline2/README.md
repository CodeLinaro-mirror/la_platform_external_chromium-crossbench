# LoadLine 2 Benchmark

LoadLine 2 is the next generation of the LoadLine benchmark. See
[LoadLine page](/config/benchmark/loadline/README.md)
for background and motivation. Compared to the first version, version 2
offers shorter execution time, more stable metrics and (some form of)
cross-platform support.

See the
[LoadLine component](https://g-issues.chromium.org/issues?q=status:open%20componentid:1670299)
for the list of open bugs.

## tl;dr: Running the Benchmark

Run "phone" workload:

```
./cb.py loadline2-phone --browser <browser>
```

Run "tablet" workload:

```
./cb.py loadline2-tablet --browser <browser>
```

The browser can be `android:chrome-canary`, `android:chrome-stable` etc. See
[crossbench docs](/README.md#browsers) for the full list of options.

*** note
Note: the benchmark requires read access to the `chrome-partner-loadline`
GCP bucket. If you are a new partner, please refer to the
[LoadLine page](/config/benchmark/loadline/README.md#cloud-bucket-access)
for instructions on getting access.
***


## Running LoadLine 2 on iOS devices

To ensure metric stability and reduce noise, LoadLine 2 uses some Chrome-only
and Android-only features. So it's not possible to run it on an iOS device as
is.

But comparisons between platforms may still be useful, so we released a
separate version of the benchmark, called "LoadLine 2 WebAPI", which can be run
on both Android and iOS devices (with some additional setup). Note this is not
the same benchmark as "normal" LoadLine 2, and there's no simple way to convert
LoadLine 2 WebAPI scores into LoadLine 2 scores. To compare web page loading
performance between iOS and Android, run LoadLine 2 WebAPI on both iOS and
Android device.

See [LoadLine 2 WebAPI](loadline2-webapi.md) for running instructions.

## Metric Details

There can be different definitions of what it means for the page to be "fully
loaded". Some of them involve being visually complete, others require being able
to interact with the page. We think that both are important, so in LoadLine 2,
we track two moments for each page: one when an important element on the page
(it can be the element that triggers LCP but not necessarily) becomes visible
("visual mark"), another when an interactive element (usually a button) on the
page becomes functional ("interactive mark").

For each mark, we then compute a score. The score equals **(60 seconds) /
(mark time - navigation time)**, so the faster the load the higher the score.

Each page's scores are averaged over all runs using an arithmetic mean. Finally,
the total benchmark score is computed as a geomean of visual and interactive
metrics from all 5 pages.

## Thermals

Depending on your device, ambient temperature and overall setup, you can
experience thermal issues while running the benchmark. If you observe large
instability in scores or unexplained score drops, consider the following:

* Insert cooldown periods between runs: e.g. `--cool-down-time 10s`

* Run the benchmark with fewer repetitions (but keep in mind that this increases
the variance of the final score): e.g. `--repeat 20`

## Trace analysis

Each iteration of the benchmark leaves a Perfetto trace (located in
`<results dir>/runs/*/perfetto.trace.pb.gz`) that can be opened with
[Perfetto UI](https://ui.perfetto.dev). We recommend enabling the
[org.chromium.LoadLine2](https://ui.perfetto.dev/#!/plugins/org.chromium.LoadLine2)
plugin when opening traces, to get a visual overview of each metric in the UI.

By default, traces contain only Chrome trace events from a limited set of
categories necessary to compute metrics. To get a more detailed system-wide
traces, run a debug version of the benchmark with the following command:

```
./cb.py loadline2-phone-debug --browser <browser>
```

Note that collecting detailed traces incurs some overhead, so the benchmark
scores will likely be lower than in the default configuration.

## Debugging / Alternative running options

Crossbench is a powerful tool that supports many knobs to control benchmark
execution. Note that while LoadLine 2 can be run in multiple different
configurations for debugging/experimentation purposes (with custom configs,
custom playback options etc), the scores obtained in the process will likely
be non-comparable with the standard scores. To ensure that your change actually
improves LoadLine2 scores, do a "clean" run (i.e. no additional flags, no
changes to configs).

That said, here's a (non-exhaustive) list of common flags:

| Flag | Description |
|-|-|
|`--repeat`| Number of repetitions of each story (50 by default) |
|`--story` | Run only a subset of pages (regex supported) |
|`--deterministic`| Provide some flags to Chrome that make its behaviour more deterministic (although less realistic) |
|`--step-by-step-mode`| Pause before each benchmark step (useful for debugging web page behavior)|
