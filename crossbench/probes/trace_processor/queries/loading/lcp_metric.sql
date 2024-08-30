SELECT dur / 1e6 AS lcp_ms
FROM slice
WHERE name = 'PageLoadMetrics.NavigationToLargestContentfulPaint'
ORDER BY ts
LIMIT 1;

