# LoadLine 2 Benchmark

LoadLine 2 is the next generation of the LoadLine benchmark. The goal of the
benchmark is to facilitate web performance optimization based on a realistic
workload. The benchmark has two workload variants:

*   General-purpose workload representative of the web usage on mobile phones
    ("phone");

*   Android Tablet web performance workload ("tablet").

Compared to the first version, version 2 offers shorter execution time, more
stable metrics and (some form of) cross-platform support.

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

## Cloud bucket access

To maintain reproducibility, the benchmark uses the
[web page replay](https://chromium.googlesource.com/webpagereplay/+/HEAD/README.md)
mechanism. Archives of the web pages are stored in the
`chrome-partner-loadline` cloud bucket, so access to that bucket is required
to run LoadLine 2. Please request access
[here](https://docs.google.com/forms/d/e/1FAIpQLSdCb1LYPlDEKuOd1lP21yZ9YDEvjq-9W0a5X9k7QxM_YjskzA/viewform?usp=header).

After getting access, run

```
gcloud auth application-default login --disable-quota-project
```

on your workstation (has to be done only once).

If you observe "Can't reach this page" or similar errors, try the following
alternative commands:

```
gcloud auth application-default login --disable-quota-project --no-launch-browser
```
or
```
gcloud auth application-default login --disable-quota-project --no-browser
```

## Technical details

### Background

Web is one of the most important use cases on mobile devices. Page loading speed
represents a crucial part of user experience, and is not well covered by
existing benchmarks (Speedometer, Jetstream, MotionMark). Experiments show that
raw CPU performance does not always result in faster web loading speeds, since
it's a complex highly parallelized process that stresses a lot of browser and OS
components and their interactions. Hence the need for a dedicated web loading
benchmark that will enable us to compare devices, track improvements across OS
and browser releases.

### Workload

We aimed for two configurations:

*   **Representative mobile Web on Android usage (~5 pages)**

    Aimed at covering loading scenarios representative of real web workloads and
    user environments on Android mobile phones.

*   **Android Tablet web performance (~5 pages)**

    A set of larger desktop-class workloads intended for tablet/large screen
    devices running Android.

The biggest challenges we faced in achieving this goal were:

*   **Representativeness**: How do we determine a representative set of web
    sites given the humongous corpus of websites whose overall distribution is
    not thoroughly understood.
*   **Metrics** Existing page load metrics generalize well for O(millions) of
    page loads across a variety of sites, but are poor fit to judge performance
    of a specific site
*   **Noise**: The web evolves. To ensure the benchmark workloads stay
    consistent over time, we chose to use recorded & replayed workloads.
    However, page load is very complex and indeterministic so naive replays are
    often not consistent.

### Site Selection

We did a thorough analysis to ensure we select relevant and representative
sites. Our aspiration was to understand the distribution of the most important
CUJs and performance characteristics on the web and use this knowledge to elect
a small number of representative CUJs, such that their performance
characteristics maximize coverage of the distribution.

Practically, we evaluated ~50 prominent sites across a number of different
characteristics (dimensions) via trace-based analysis, cross-checking via field
data. We clustered similar pages and selected representatives for important
clusters. In the end, this was a manual selection aided by algorithmic
clustering/correlation analysis.

We looked at over 20 dimensions for suitability and relevance to our site
selection, and low correlation between dimensions. Of these, we chose 6 primary
metrics that we optimized coverage on: Website type, workload size (CPU time),
DOM/Layout complexity (#nodes), JavaScript heap size, time spent in V8, time
spent in V8 callbacks into Blink. Secondarily, we included utilization of web
features and relevant mojo interfaces, e.g. Video, cookies, main/subframe
communication, input events, frame production, network requests, etc.

In the end we selected 5 sites for each configuration which we plan to extend in
the future.

#### Mobile

| Page (mobile version)      | CUJ               | Performance characteristics |
| -------------------------- | ------------------ | -------------------------- |
| amazon.co.uk <br> (product page) | Shopping           | * average page load, large workload, large DOM/JS (but heavier on DOM) <br> * high on OOPIFs, input, http(s) resources, frame production |
| cnn.com <br> (article)           | News               | * slow page load, large workload, large DOM/JS (but heavier on JS) <br> * high on iframes, main frame, local storage, cookies, http(s) resources |
| wikipedia.org <br> (article)     | Reference work     | * fast page load, small workload, large DOM, small JS <br> * high on input <br> * low on iframes, http(s) resources, frame production |
| globo.com <br> (homepage)        | News / web portal  | * slow page load, large workload, small DOM, large JS <br> * high on iframes, OOPIFs, http(s) resources, frame production, cookies |
| google.com <br> (results)        | Search             | * fast page load, average workload, average DOM + JS <br> * high on main frame, local storage, video |

#### Tablet

| Page (desktop version)     | CUJ          | Performance characteristics      |
| -------------------------- | ------------ | -------------------------------- |
| amazon.co.uk <br> (product page) | Shopping     | * average page load, large workload, large DOM, average JS <br> * high on OOPIFs, http(s) resources, frame production |
| cnn.com <br> (article)           | News         | * slow page load, large workload, large DOM/JS (but heavier on JS) <br> * high on iframes, local storage, video, frame production, cookies |
| docs.google.com <br> (document)  | Productivity | * slow page load, large workload, large DOM + JS (heavier on JS) <br> * high on main frame <br> * high on font resources |
| google.com <br> (results)        | Search       | * fast page load, low workload, low DOM + JS <br> * high on main frame, local storage <br> * low on video |
| youtube.com<br> (video)         | Media        | * slow page load, very high workload, large DOM, small JS heap, average JS time <br> * high on video |

### Metrics and the final score

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

## Alternative running options

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
