-- Perfetto script that exports pprof profiles per story, only including
-- score-relevant time intervals.

SELECT
  IMPORT ('chrome.speedometer');

DROP VIEW IF EXISTS speedometer_perf_sample_span;

CREATE VIEW
  speedometer_perf_sample_span AS
SELECT
  ts,
  0 as dur,
  utid,
  cpu,
  callsite_id
FROM
  perf_sample
UNION
SELECT
  ts,
  0 as dur,
  utid,
  cpu,
  callsite_id
FROM
  instruments_sample;

DROP TABLE IF EXISTS speedometer_sample;

CREATE VIRTUAL TABLE speedometer_sample USING SPAN_JOIN (chrome_speedometer_measure, speedometer_perf_sample_span);

select
-- WRITE_FILE depends on trace_processor's --dev flag
  WRITE_FILE (
    suite_name || '.pprof',
    (
      SELECT
        EXPERIMENTAL_PROFILE (
          CAT_STACKS (
            suite_name || '.' || test_name || '.' || measure_type,
            IIF (
              INSTR (p.name, "(") > 0,
              SUBSTR (p.name, 0, INSTR (p.name, "(") -1),
              p.name
            ),
            IIF (
              INSTR (t.name, " 0x") > 0,
              SUBSTR (t.name, 0, INSTR (t.name, " 0x") -1),
              t.name
            ),
            STACK_FROM_STACK_PROFILE_CALLSITE (callsite_id)
          ),
          'samples',
          'count',
          1
        ) AS profile
      FROM
        speedometer_sample s
        JOIN thread t on s.utid = t.utid
        JOIN process p on t.upid = p.upid
      WHERE
        suite_name = m.suite_name
    )
  )
FROM
  chrome_speedometer_measure as m
GROUP BY
  suite_name;