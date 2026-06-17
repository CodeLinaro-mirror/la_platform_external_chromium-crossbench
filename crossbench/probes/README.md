# Crossbench Probes

Probes extract performance metrics (e.g., memory usage, traces, power) from
stories and browsers during a benchmark run.

## Architecture

* `Probe` ([`probe.py`](./probe.py)): The configuration and orchestration
  interface. Handles validation and data merging across repetitions, stories,
  and browsers.
* `ProbeContext` ([`probe_context.py`](./probe_context.py)): The active
  collection phase for a single run or browser session. Handles the actual
  lifecycle (`setup`, `start`, `stop`, `teardown`).
* `ProbeResult` ([`results.py`](./results.py)): Standardized output data
  structure managing local and remote result files.

## Adding a New Probe

1. Subclass `Probe` with a unique `NAME`.
2. Subclass `ProbeContext` to implement  the main hooks (
   `setup()`, `start()`, `stop()`, and  `teardown()`).
3. Override `Probe.get_context_cls()` to return your custom context class.
4. Add basic tests to cover default arguments and Probe input parsing.
