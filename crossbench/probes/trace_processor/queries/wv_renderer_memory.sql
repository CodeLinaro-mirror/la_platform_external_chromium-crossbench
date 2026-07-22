INCLUDE PERFETTO MODULE ext.webview_startup;
INCLUDE PERFETTO MODULE linux.memory.high_watermark;
INCLUDE PERFETTO MODULE linux.memory.process;

-- Find the timestamp of when "Destroy WebView" was clicked
WITH destroy_event AS (
  SELECT ts
  FROM android_logs
  WHERE msg LIKE '%Destroy WebView%'
    AND tag LIKE '%uiautomator%'
  ORDER BY ts ASC
  LIMIT 1
),
-- Retrieve the latest memory metrics for the WebView renderer process
-- just before the 'Destroy WebView' event occurs.
latest_memory AS (
  SELECT
    m.upid,
    m.anon_rss AS rss_anon_renderer_bytes,
    m.file_rss AS rss_file_renderer_bytes,
    m.shmem_rss AS rss_shmem_renderer_bytes,
    m.swap AS swap_renderer_bytes,
    m.anon_rss_and_swap AS rss_anon_plus_swap_renderer_bytes
  FROM memory_rss_and_swap_per_process m
  JOIN destroy_event d
  WHERE m.ts < d.ts
    AND m.process_name LIKE '%webview%sandboxed%'
  ORDER BY m.ts DESC
  LIMIT 1
),
latest_hwm AS (
  SELECT
    h.rss_high_watermark AS rss_hwm_renderer_bytes
  FROM memory_rss_high_watermark_per_process h
  JOIN destroy_event d
  JOIN latest_memory m ON h.upid = m.upid
  WHERE h.ts < d.ts
  ORDER BY h.ts DESC
  LIMIT 1
),
-- Retrieve the memory metrics for the WebView renderer process
-- after the WebView has been destroyed.
empty_renderer_memory AS (
  SELECT
    m.anon_rss AS rss_anon_empty_renderer_bytes,
    m.file_rss AS rss_file_empty_renderer_bytes,
    m.shmem_rss AS rss_shmem_empty_renderer_bytes,
    m.swap AS swap_empty_renderer_bytes,
    m.anon_rss_and_swap AS rss_anon_plus_swap_empty_renderer_bytes
  FROM memory_rss_and_swap_per_process m
  JOIN latest_memory lm ON m.upid = lm.upid
  ORDER BY m.ts DESC
  LIMIT 1
),
-- Retrieve the memory metrics for the WebView browser process
-- after the WebView has been destroyed.
empty_browser_memory AS (
  SELECT
    m.anon_rss AS rss_anon_empty_browser_bytes,
    m.file_rss AS rss_file_empty_browser_bytes,
    m.shmem_rss AS rss_shmem_empty_browser_bytes,
    m.swap AS swap_empty_browser_bytes,
    m.anon_rss_and_swap AS rss_anon_plus_swap_empty_browser_bytes
  FROM memory_rss_and_swap_per_process m
  JOIN webview_startup_start_slice AS start_slice ON m.upid = start_slice.upid
  ORDER BY m.ts DESC
  LIMIT 1
)
SELECT
  rss_anon_renderer_bytes,
  rss_file_renderer_bytes,
  rss_shmem_renderer_bytes,
  swap_renderer_bytes,
  rss_anon_plus_swap_renderer_bytes,
  rss_hwm_renderer_bytes,
  rss_anon_empty_renderer_bytes,
  rss_file_empty_renderer_bytes,
  rss_shmem_empty_renderer_bytes,
  swap_empty_renderer_bytes,
  rss_anon_plus_swap_empty_renderer_bytes,
  rss_anon_empty_browser_bytes,
  rss_file_empty_browser_bytes,
  rss_shmem_empty_browser_bytes,
  swap_empty_browser_bytes,
  rss_anon_plus_swap_empty_browser_bytes
FROM latest_memory, latest_hwm, empty_renderer_memory, empty_browser_memory;
