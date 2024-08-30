DROP VIEW IF EXISTS navigation_start;

CREATE VIEW navigation_start AS
SELECT MIN(ts) AS navigation_start
FROM slice
WHERE name = 'PageLoadMetrics.NavigationToLargestContentfulPaint';


DROP VIEW IF EXISTS last_navigation_start;

CREATE VIEW last_navigation_start AS
SELECT MAX(ts) AS last_navigation_start
FROM slice
WHERE name = 'PageLoadMetrics.NavigationToLargestContentfulPaint';