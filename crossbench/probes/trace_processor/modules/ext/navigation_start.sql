DROP VIEW IF EXISTS navigation_start;

CREATE VIEW navigation_start AS
SELECT MIN(ts) AS navigation_start
FROM slice
WHERE name = 'PageLoadMetrics.NavigationToLargestContentfulPaint';