-- Trace categories needed:
--   * benchmark
--   * blink.user_timing
--   * loading
--   * devtools.timeline
--   * disabled-by-default-devtools.timeline
--   * v8
CREATE OR REPLACE PERFETTO FUNCTION get_first_presentation_time_for_event(
  name STRING)
RETURNS INT
AS
WITH
  event AS (
    SELECT ts
    FROM slice
    WHERE name = $name AND cat = 'blink.user_timing'
    ORDER BY ts
    LIMIT 1
  ),
  candidate_presentation_time AS (
    SELECT a.ts + a.dur AS ts
    FROM slice s, ancestor_slice(s.id) a
    WHERE
      s.name = 'Commit'
      AND a.name = 'PipelineReporter'
      AND s.depth - 1 = a.depth
      AND s.ts > (SELECT ts FROM event)
    ORDER BY s.ts
    LIMIT 1
  )
SELECT ts
FROM slice
WHERE
  name = 'Display::FrameDisplayed'
  AND ts >= (SELECT ts FROM candidate_presentation_time)
ORDER BY ts
LIMIT 1;
