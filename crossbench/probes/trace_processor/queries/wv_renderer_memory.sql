INCLUDE PERFETTO MODULE linux.memory.process;

-- Find the timestamp of when "Destroy WebView" was clicked
WITH destroy_event AS (
  SELECT ts
  FROM android_logs
  WHERE msg LIKE '%Destroy WebView%'
    AND tag LIKE '%uiautomator%'
  ORDER BY ts ASC
  LIMIT 1
)
-- Retrieve the latest memory metrics for the WebView renderer process
-- just before the 'Destroy WebView' event occurs.
SELECT
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
LIMIT 1;
