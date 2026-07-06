INCLUDE PERFETTO MODULE ext.webview_startup;
INCLUDE PERFETTO MODULE linux.memory.high_watermark;
INCLUDE PERFETTO MODULE linux.memory.process;

WITH
  mem_at_start AS (
    -- Get memory values at the beginning of start_slice for the identified process
    SELECT
      m.anon_rss,
      m.file_rss,
      m.shmem_rss,
      COALESCE(m.swap, 0) AS swap
    FROM memory_rss_and_swap_per_process m
    JOIN webview_startup_start_slice AS start_slice ON m.upid = start_slice.upid
    WHERE m.ts <= start_slice.ts
    ORDER BY m.ts DESC
    LIMIT 1
  ),
  mem_at_end AS (
    -- Get memory values at the end of end_slice for the same process
    SELECT
      m.anon_rss,
      m.file_rss,
      m.shmem_rss,
      COALESCE(m.swap, 0) AS swap
    FROM memory_rss_and_swap_per_process m
    JOIN webview_startup_start_slice AS start_slice ON m.upid = start_slice.upid
    CROSS JOIN webview_startup_end_slice AS end_slice
    WHERE m.ts >= end_slice.end_ts
    ORDER BY m.ts
    LIMIT 1
  ),
  hwm_at_end AS (
    -- Get rss high watermark value at the end of end_slice for the same process
    SELECT
      h.rss_high_watermark
    FROM memory_rss_high_watermark_per_process h
    JOIN webview_startup_start_slice AS start_slice ON h.upid = start_slice.upid
    CROSS JOIN webview_startup_end_slice AS end_slice
    WHERE h.ts >= end_slice.end_ts
    ORDER BY h.ts
    LIMIT 1
  ),
  diffs AS (
    SELECT
      (mem_at_end.anon_rss - mem_at_start.anon_rss) AS rss_anon_startCL_diff_bytes,
      (mem_at_end.file_rss - mem_at_start.file_rss) AS rss_file_startCL_diff_bytes,
      (mem_at_end.shmem_rss - mem_at_start.shmem_rss) AS rss_shmem_startCL_diff_bytes,
      (mem_at_end.swap - mem_at_start.swap) AS swap_startCL_diff_bytes
    FROM mem_at_start, mem_at_end
  )
SELECT
  rss_anon_startCL_diff_bytes,
  rss_file_startCL_diff_bytes,
  rss_shmem_startCL_diff_bytes,
  swap_startCL_diff_bytes,
  (rss_anon_startCL_diff_bytes + swap_startCL_diff_bytes) AS rss_anon_plus_swap_startCL_diff_bytes,
  hwm_at_end.rss_high_watermark AS rss_hwm_startCL_bytes
FROM diffs, hwm_at_end;
