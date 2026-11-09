# Browser Startup Benchmark

This benchmark measures browser startup paint latencies (`Startup.BrowserWindow.FirstPaint`, `InitialWebUI.Startup.BrowserWindow.FirstPaint`, `Startup.FirstWebContents.NonEmptyPaint3`, and `InitialWebUI.Startup.ReloadButton.FirstContentfulPaint`), New Tab Page load latencies (`NewTabPage.LoadTime.FirstContentfulPaint2`, `NewTabPage.MainUi.ShownTime`, `NewTabPage.LoadTime.Startup`, `NewTabPage.LoadTime.NewTab`, and `NewTabPage.OneGoogleBar.ShownTime`), and frame smoothness metrics (`Graphics.Smoothness.PercentDroppedFrames3.*`) across startup stories (`newtab_startup`, `blank_startup`, and `google_startup`). It compares a **baseline** configuration against one with the **InitialWebUI** feature enabled.

## Running the Benchmark

This configuration uses the `browser-startup` subcommand, which automatically loads `config/benchmark/browser_startup/probe.hjson` and `config/benchmark/browser_startup/story.hjson`. To run the benchmark locally and compare the variants using Poetry, first install the required dependencies:

```bash
poetry install
```

Then run the benchmark (passing `--separate` so each startup story launches a fresh browser instance):

```bash
poetry run cb browser-startup \
  --browser-config config/benchmark/browser_startup/browser.config.hjson \
  --separate \
  --env-validation=warn \
  --repeat=30
```

### Benchmarking Post-Startup New Tab (`NewTabPage.LoadTime.NewTab`) and Smoothness (`Graphics.Smoothness.*`)

Because `cc::FrameSequenceMetrics` only emits `Graphics.Smoothness.PercentDroppedFrames3.*` after an active animation or scroll sequence reaches `kMinFramesForThroughputMetric = 100` frames (~1.67s at 60Hz) and `NewTabPage.LoadTime.NewTab` is only recorded for tabs opened after `AfterStartupTaskUtils::IsBrowserStartupComplete()`, use `story_interactive.hjson` when benchmarking post-startup New Tab opening and animation smoothness:

```bash
poetry run cb browser-startup \
  --browser-config config/benchmark/browser_startup/browser.config.hjson \
  --page-config config/benchmark/browser_startup/story_interactive.hjson \
  --no-start-browser \
  --separate \
  --env-validation=warn \
  --repeat=30
```

> [!NOTE]
> If you are in a Chromium development environment with `depot_tools` (`vpython3`), you can run `./cb.py browser-startup ...` directly without `poetry install`.

## Interpreting Results

After the run finishes, Crossbench outputs a path to the results directory (e.g., `results/latest/`) and logs a `Browser Startup Summary` table (`startup_summary.csv`).
Within the `trace_processor/` sub-directory, look for the following CSV (or `.json`) files containing per-run metrics:

- `browser_window_first_paint.csv` (`Startup.BrowserWindow.FirstPaint`): Contains `browser_window_first_paint_ms` (CPU paint recording in `BrowserView::PaintChildren`) for each run and story.
- `initial_webui_browser_window_first_paint.csv` (`InitialWebUI.Startup.BrowserWindow.FirstPaint`): Contains `initial_webui_browser_window_first_paint_ms` (actual window presentation on screen via `BrowserView::OnFirstPresentation`) for each run and story.
- `first_web_contents_non_empty_paint.csv` (`Startup.FirstWebContents.NonEmptyPaint3`): Contains `first_web_contents_non_empty_paint_ms` for each run and story.
- `reload_button_fcp.csv` (`InitialWebUI.Startup.ReloadButton.FirstContentfulPaint`): Contains `reload_button_fcp_ms` for each run and story (emitted only when `InitialWebUI` + `WebUIReloadButton` are enabled).
- `ntp_fcp.csv` (`NewTabPage.LoadTime.FirstContentfulPaint2`): Contains `ntp_fcp_ms` for New Tab Page stories.
- `ntp_main_ui_shown_time.csv` (`NewTabPage.MainUi.ShownTime`): Contains `ntp_main_ui_shown_time_ms` for New Tab Page stories.
- `ntp_load_time_startup.csv` (`NewTabPage.LoadTime.Startup`): Contains `ntp_load_time_startup_ms` for the initial startup New Tab Page (`newtab_startup`).
- `ntp_load_time_new_tab.csv` (`NewTabPage.LoadTime.NewTab`): Contains `ntp_load_time_new_tab_ms` for post-startup New Tab Page navigations (`newtab_interactive`).
- `ntp_one_google_bar_shown_time.csv` (`NewTabPage.OneGoogleBar.ShownTime`): Contains `ntp_one_google_bar_shown_time_ms` when the OneGoogleBar finishes rendering on the New Tab Page.
- `graphics_smoothness_percent_dropped_frames_all_sequences.csv` (`Graphics.Smoothness.PercentDroppedFrames3.AllSequences`), `graphics_smoothness_percent_dropped_frames_all_animations.csv` (`Graphics.Smoothness.PercentDroppedFrames3.AllAnimations`), `graphics_smoothness_percent_dropped_frames_all_interactions.csv` (`Graphics.Smoothness.PercentDroppedFrames3.AllInteractions`), and `webium_graphics_smoothness_percent_dropped_frames_all_sequences.csv` (`Webium.Graphics.Smoothness.PercentDroppedFrames3.AllSequences`): Contain frame drop percentages for stories that drive $\ge 100$ frames of animation or scroll (`story_interactive.hjson`).
