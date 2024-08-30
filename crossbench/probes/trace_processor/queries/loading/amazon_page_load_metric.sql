-- This metric returns the time it takes for the "main" JS script to finish the
-- execution - this is when the page becomes interactive.
SELECT IMPORT('ext.first_presentation_time');
SELECT IMPORT('ext.navigation_start');

WITH
  js_ready AS (
    SELECT MAX(ts) AS js_ready
    FROM slice
    WHERE
      name = 'v8.run'
      AND EXTRACT_ARG(arg_set_id, 'debug.fileName') = 'https://www.amazon.co.uk/NIVEA-Suncream-Spray-Protect-Moisture/dp/B001B0OJXM'
  )
SELECT (get_next_presentation_time(js_ready) - navigation_start) / 1e6 AS js_ready_ms
FROM navigation_start, js_ready;

