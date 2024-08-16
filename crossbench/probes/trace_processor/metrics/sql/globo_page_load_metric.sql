-- This metric returns the time the cookie banner takes to disappear.
SELECT IMPORT('ext.navigation_start');

DROP VIEW IF EXISTS globo_page_load_metric_output;

CREATE PERFETTO VIEW globo_page_load_metric_output AS
SELECT GloboPageLoadMetric(
  'cookie_banner_gone_ms', (
      WITH
        cookie_banner_gone AS (
            SELECT ts AS cookie_banner_gone
            FROM slice
            WHERE name = 'cookie_banner_gone'
        )
      SELECT (cookie_banner_gone - navigation_start) / 1e6
      FROM navigation_start, cookie_banner_gone
  )
);