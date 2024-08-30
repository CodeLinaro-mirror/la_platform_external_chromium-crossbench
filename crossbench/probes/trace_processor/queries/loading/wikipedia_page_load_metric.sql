-- This metric returns the timestamp of the last important event (including
-- image paint, JS script runs etc.) since the beginning of the page load.
SELECT IMPORT('ext.navigation_start');

WITH
  script_run AS (
      SELECT ts + dur AS script_run
      FROM slice
      WHERE
          name = 'v8.run'
          AND EXTRACT_ARG(arg_set_id, 'debug.fileName') GLOB '*ext.cx.entrypoints.languagesearcher.init*'
  ),
  img_load AS (
      SELECT ts
      FROM slice
      WHERE
          name = 'PaintImage'
          AND EXTRACT_ARG(arg_set_id, 'debug.data.url') GLOB '*Taylor_Swift_at_the_2023_MTV_Video_Music_Awards*'
  ),
  img_next_af AS (
      SELECT id
      FROM slice, img_load
      WHERE
          name = 'AnimationFrame'
          AND slice.ts > img_load.ts
      order by slice.ts
      LIMIT 1
  ),
  img_presentation AS (
      SELECT ts AS img_presentation
      FROM img_next_af, DIRECTLY_CONNECTED_FLOW(img_next_af.id) AS flow, slice
      WHERE slice.id = flow.slice_in
  )
SELECT (MAX(img_presentation, script_run) - navigation_start) / 1e6 AS last_important_event_ms
FROM navigation_start, img_presentation, script_run;

