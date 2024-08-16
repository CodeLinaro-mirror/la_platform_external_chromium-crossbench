-- This metric returns the time it takes for the "main" JS script to finish the
-- execution - this is when the page becomes interactive.
SELECT IMPORT('ext.navigation_start');

DROP VIEW IF EXISTS amazon_page_load_metric_output;

CREATE PERFETTO VIEW amazon_page_load_metric_output AS
SELECT AmazonPageLoadMetric(
  'js_ready_ms', (
      WITH
        js_ready AS (
          SELECT MAX(ts + dur) AS js_ready
          FROM slice
          WHERE
            name = 'v8.run'
            AND EXTRACT_ARG(arg_set_id, 'debug.fileName') = 'https://www.amazon.co.uk/NIVEA-Suncream-Spray-Protect-Moisture/dp/B001B0OJXM'
        )
      SELECT (js_ready - navigation_start) / 1e6
      FROM navigation_start, js_ready
  )
);