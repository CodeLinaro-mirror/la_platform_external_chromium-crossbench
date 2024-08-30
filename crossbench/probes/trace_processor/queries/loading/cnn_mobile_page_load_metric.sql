-- This metric returns the time the headline text element takes to show up.
SELECT IMPORT('ext.first_presentation_time');
SELECT IMPORT('ext.navigation_start');

SELECT
  (get_first_presentation_time_for_event('maincontent.created')
      - navigation_start) / 1e6 AS text_shown_ms
FROM navigation_start;

