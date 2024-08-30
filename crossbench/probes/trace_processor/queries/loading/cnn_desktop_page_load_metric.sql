-- This metric returns the time the headline text element takes to show up
-- after the second (which is also the last) page load.
-- The first page load is "incomplete" - it shows the cookie banner and
-- doesn't load some of the content like ads. We click on the cookie
-- banner, triggering the second ("complete") page load.
SELECT IMPORT('ext.first_presentation_time');
SELECT IMPORT('ext.navigation_start');

DROP VIEW IF EXISTS last_navigation_maincontent_created;
CREATE VIEW last_navigation_maincontent_created AS
SELECT ts AS last_navigation_maincontent_created
FROM slice
WHERE
    name = 'maincontent.created'
    AND cat = 'blink.user_timing'
    AND ts > (SELECT last_navigation_start FROM last_navigation_start)
ORDER BY ts
LIMIT 1;

SELECT
  (get_next_presentation_time(last_navigation_maincontent_created)
      - last_navigation_start) / 1e6 AS text_shown_ms
FROM last_navigation_start, last_navigation_maincontent_created;

