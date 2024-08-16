-- This metric returns the time the cookie banner takes to disappear.
SELECT IMPORT('ext.first_presentation_time');
SELECT IMPORT('ext.navigation_start');

DROP VIEW IF EXISTS youtube_page_load_metric_output;

CREATE PERFETTO VIEW youtube_page_load_metric_output AS
SELECT YoutubePageLoadMetric(
  'cookie_banner_gone_ms', (
      SELECT
        (get_first_presentation_time_for_event('cookie_banner_gone') - navigation_start) / 1e6
      FROM navigation_start
  )
);