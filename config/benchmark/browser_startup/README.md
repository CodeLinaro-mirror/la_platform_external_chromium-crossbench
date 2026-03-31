# Browser Startup Benchmark

This benchmark measures the time to the first non-empty paint (`Startup.BrowserWindow.FirstPaint`) for the browser startup sequence. It compares a **baseline** configuration against one with the **InitialWebUI** feature enabled.

## Running the Benchmark

This configuration uses the `loading` subcommand. To run the benchmark locally and compare the variants:

```bash
poetry run cb loading \
  --browser-config config/benchmark/browser_startup/browser.config.hjson \
  --probe-config config/benchmark/browser_startup/probe.hjson \
  --page-config config/benchmark/browser_startup/story.hjson \
  --env-validation=warn \
  --repeat=30
```

## Interpreting Results

After the run finishes, Crossbench outputs a path to the results directory.
Within the `trace_processor/` sub-directory, look for `browser_window_first_paint.csv` (or `.json`). This file contains the calculated `duration_ms` metric for each run, which you can use to directly compare the performance of each variant.
