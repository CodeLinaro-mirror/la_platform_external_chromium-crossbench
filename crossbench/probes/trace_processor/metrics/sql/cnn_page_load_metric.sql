-- This metric returns the time the headline text element takes to show up.
SELECT IMPORT('ext.first_presentation_time');
SELECT IMPORT('ext.navigation_start');

DROP VIEW IF EXISTS cnn_page_load_metric_output;

CREATE PERFETTO VIEW cnn_page_load_metric_output AS
SELECT CNNPageLoadMetric(
  'text_shown_ms', (
      SELECT
        (get_first_presentation_time_for_event('maincontent.created') - navigation_start) / 1e6
      FROM navigation_start
  )
);