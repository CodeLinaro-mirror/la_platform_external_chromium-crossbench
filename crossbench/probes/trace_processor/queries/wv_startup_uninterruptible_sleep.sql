 WITH
          start_slice AS (
              SELECT ts, tt.utid
              FROM slice s
              JOIN
                thread_track tt
                ON s.track_id = tt.id
              JOIN
                thread t
                ON tt.utid = t.utid
              WHERE
                s.name LIKE '%WebViewChromiumAwInit.startChromiumLockedAsync_task1%'
                OR s.name LIKE '%WebViewChromiumAwInit.startChromiumLockedSync%'
              LIMIT 1
          ),
          end_slice AS (
              SELECT (ts + dur) as end_ts
              FROM slice
              WHERE
                name LIKE '%WebViewChromiumAwInit.startChromiumLockedAsync_task5%'
                OR name LIKE '%WebViewChromiumAwInit.startChromiumLockedSync%'
              LIMIT 1
          ),
          thread_state_breakdown AS (
            SELECT
              tsb.state,
              SUM(tsb.dur) AS total_dur_ns
            FROM
              thread_state tsb
            CROSS JOIN
              start_slice
            CROSS JOIN
              end_slice
            WHERE
              tsb.utid = start_slice.utid
              AND tsb.ts < end_slice.end_ts
              AND (tsb.ts + tsb.dur) > start_slice.ts
            GROUP BY
              tsb.state
          )
        SELECT (total_dur_ns / 1000000.0) AS D_thread_state_startCL_dur_ms FROM thread_state_breakdown WHERE state = 'D';
