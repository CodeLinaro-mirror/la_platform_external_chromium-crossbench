-- Copyright 2025 The Chromium Authors
-- Use of this source code is governed by a BSD-style license that can be
-- found in the LICENSE file.

-- Perfetto script that exports pprof profiles per story, only including
-- score-relevant time intervals.
SELECT
  IMPORT ('chrome.speedometer');

DROP VIEW IF EXISTS speedometer_perf_sample_span;

CREATE VIEW
  speedometer_perf_sample_span AS
SELECT
  ts,
  0 AS dur,
  utid,
  cpu,
  callsite_id
FROM
  perf_sample
-- Use UNION ALL, since we either get perf OR instruments samples.
UNION ALL
SELECT
  ts,
  0 AS dur,
  utid,
  cpu,
  callsite_id
FROM
  instruments_sample;

DROP TABLE IF EXISTS speedometer_sample;

CREATE VIRTUAL TABLE speedometer_sample USING SPAN_JOIN (chrome_speedometer_measure, speedometer_perf_sample_span);

-- WRITE_FILE depends on trace_processor's --dev flag
SELECT
  suite_name,
  file_name,
  WRITE_FILE(file_name, profile) AS file_size
FROM (
  SELECT
    m.suite_name,
    m.suite_name || '.pprof' AS file_name,
    (
      SELECT
        EXPERIMENTAL_PROFILE(
          CAT_STACKS(
            m.suite_name || '.' || test_name || '.' || measure_type,
            IIF(
              INSTR(p.name, "(") > 0,
              SUBSTR(p.name, 0, INSTR(p.name, " (")),
              p.name
            ),
            IIF(
              INSTR(t.name, " 0x") > 0,
              SUBSTR(t.name, 0, INSTR(t.name, " 0x")),
              t.name
            ),
            STACK_FROM_STACK_PROFILE_CALLSITE(callsite_id)
          ),
          'samples',
          'count',
          1
        )
      FROM
        speedometer_sample s
        JOIN thread t ON s.utid = t.utid
        JOIN process p ON t.upid = p.upid
      WHERE
        s.suite_name = m.suite_name
    ) AS profile
  FROM (
    SELECT DISTINCT
      suite_name
    FROM
      chrome_speedometer_measure
  ) m
)
WHERE
  profile IS NOT NULL;
