-- This metric returns the time the cookie banner takes to disappear.
SELECT IMPORT('ext.first_presentation_time');
SELECT IMPORT('ext.navigation_start');

SELECT
  (get_first_presentation_time_for_event('cookie_banner_gone')
      - navigation_start) / 1e6 AS cookie_banner_gone_ms
FROM navigation_start;

