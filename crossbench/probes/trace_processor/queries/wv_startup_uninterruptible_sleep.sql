INCLUDE PERFETTO MODULE ext.webview_startup;

WITH
  thread_state_breakdown AS (
    SELECT
      tsb.state,
      SUM(tsb.dur) AS total_dur_ns
    FROM
      thread_state tsb
    CROSS JOIN
      webview_startup_start_slice AS start_slice
    CROSS JOIN
      webview_startup_end_slice AS end_slice
    WHERE
      tsb.utid = start_slice.utid
      AND tsb.ts < end_slice.end_ts
      AND (tsb.ts + tsb.dur) > start_slice.ts
    GROUP BY
      tsb.state
  )
SELECT (total_dur_ns / 1000000.0) AS D_thread_state_startCL_dur_ms
FROM thread_state_breakdown
WHERE state = 'D';
