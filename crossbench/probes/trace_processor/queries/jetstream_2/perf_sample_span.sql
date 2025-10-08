-- Perfetto script that exports pprof profiles per story, only including
-- score-relevant time intervals.
SELECT
  IMPORT ('chrome.speedometer');

DROP VIEW IF EXISTS perf_sample_span;

CREATE VIEW
  perf_sample_span AS
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

DROP VIEW IF EXISTS jetstream_measure_iterations;

CREATE VIEW
  jetstream_measure_iterations AS
SELECT
  id,
  ts,
  dur,
  substr (name, 1, instr (name, '-iteration-') -1) as name,
  cast(
    substr (name, instr (name, '-iteration-') + 11) as integer
  ) as iteration
FROM
  slice
WHERE
  category = 'blink.user_timing'
  AND (
    name LIKE '3d-cube-SP-iteration-%'
    OR name LIKE '3d-raytrace-SP-iteration-%'
    OR name LIKE 'Air-iteration-%'
    OR name LIKE 'Babylon-iteration-%'
    OR name LIKE 'Basic-iteration-%'
    OR name LIKE 'Box2D-iteration-%'
    OR name LIKE 'FlightPlanner-iteration-%'
    OR name LIKE 'ML-iteration-%'
    OR name LIKE 'OfflineAssembler-iteration-%'
    OR name LIKE 'UniPoker-iteration-%'
    OR name LIKE 'acorn-wtb-iteration-%'
    OR name LIKE 'ai-astar-iteration-%'
    OR name LIKE 'async-fs-iteration-%'
    OR name LIKE 'babylon-wtb-iteration-%'
    OR name LIKE 'base64-SP-iteration-%'
    OR name LIKE 'bomb-workers-iteration-%'
    OR name LIKE 'cdjs-iteration-%'
    OR name LIKE 'chai-wtb-iteration-%'
    OR name LIKE 'coffeescript-wtb-iteration-%'
    OR name LIKE 'crypto-iteration-%'
    OR name LIKE 'crypto-aes-SP-iteration-%'
    OR name LIKE 'crypto-md5-SP-iteration-%'
    OR name LIKE 'crypto-sha1-SP-iteration-%'
    OR name LIKE 'date-format-tofte-SP-iteration-%'
    OR name LIKE 'date-format-xparb-SP-iteration-%'
    OR name LIKE 'delta-blue-iteration-%'
    OR name LIKE 'earley-boyer-iteration-%'
    OR name LIKE 'espree-wtb-iteration-%'
    OR name LIKE 'first-inspector-code-load-iteration-%'
    OR name LIKE 'float-mm.c-iteration-%'
    OR name LIKE 'gaussian-blur-iteration-%'
    OR name LIKE 'gbemu-iteration-%'
    OR name LIKE 'hash-map-iteration-%'
    OR name LIKE 'jshint-wtb-iteration-%'
    OR name LIKE 'json-parse-inspector-iteration-%'
    OR name LIKE 'json-stringify-inspector-iteration-%'
    OR name LIKE 'lebab-wtb-iteration-%'
    OR name LIKE 'mandreel-iteration-%'
    OR name LIKE 'multi-inspector-code-load-iteration-%'
    OR name LIKE 'n-body-SP-iteration-%'
    OR name LIKE 'navier-stokes-iteration-%'
    OR name LIKE 'octane-code-load-iteration-%'
    OR name LIKE 'octane-zlib-iteration-%'
    OR name LIKE 'pdfjs-iteration-%'
    OR name LIKE 'prepack-wtb-iteration-%'
    OR name LIKE 'raytrace-iteration-%'
    OR name LIKE 'regex-dna-SP-iteration-%'
    OR name LIKE 'regexp-iteration-%'
    OR name LIKE 'richards-iteration-%'
    OR name LIKE 'segmentation-iteration-%'
    OR name LIKE 'splay-iteration-%'
    OR name LIKE 'stanford-crypto-aes-iteration-%'
    OR name LIKE 'stanford-crypto-pbkdf2-iteration-%'
    OR name LIKE 'stanford-crypto-sha256-iteration-%'
    OR name LIKE 'string-unpack-code-SP-iteration-%'
    OR name LIKE 'tagcloud-SP-iteration-%'
    OR name LIKE 'typescript-iteration-%'
    OR name LIKE 'uglify-js-wtb-iteration-%'
  )
  AND dur > 0;

DROP VIEW IF EXISTS jetstream_measure_wasm;

CREATE VIEW
  jetstream_measure_wasm AS
SELECT
  id,
  ts,
  dur,
  substr (name, 1, instr (name, '-wasm-') + 4) as name,
  substr (name, instr (name, '-wasm-') + 6) as subtest
FROM
  slice
WHERE
  category = 'blink.user_timing'
  AND (
    name LIKE 'tsf-wasm-%'
    OR name LIKE 'richards-wasm-%'
    OR name LIKE 'quicksort-wasm-%'
    OR name LIKE 'HashSet-wasm-%'
    OR name LIKE 'gcc-loops-wasm-%'
  )
  AND dur > 0;

DROP VIEW IF EXISTS jetstream_measure;

CREATE VIEW
  jetstream_measure AS
SELECT
  id,
  ts,
  dur,
  name,
  iteration,
  IIF (rank_within_name <= 4, 'Worst4', 'Average') as subtest
FROM
  (
    SELECT
      id,
      ts,
      dur,
      name,
      iteration,
      RANK() OVER (
        PARTITION BY
          name
        ORDER BY
          dur DESC
      ) as rank_within_name
    FROM
      jetstream_measure_iterations
    WHERE
      iteration > 0
  )
UNION
SELECT
  id,
  ts,
  dur,
  name,
  iteration,
  'First' as subtest
FROM
  jetstream_measure_iterations
WHERE
  iteration = 0
UNION
SELECT
  id,
  ts,
  dur,
  name,
  0 as iteration,
  subtest
FROM
  jetstream_measure_wasm;

DROP TABLE IF EXISTS jetstream_sample;

CREATE VIRTUAL TABLE jetstream_sample USING SPAN_JOIN (jetstream_measure, perf_sample_span);

-- WRITE_FILE needs trace_processor's --dev flag.
SELECT
  WRITE_FILE (
    'jetstream.pprof',
    (
      SELECT
        EXPERIMENTAL_PROFILE (
          CAT_STACKS (
            s.name,
            s.subtest,
            p.name,
            IIF (
              instr (t.name, ' ') > 0,
              substr (t.name, 1, instr (t.name, ' ') -1),
              t.name
            ),
            STACK_FROM_STACK_PROFILE_CALLSITE (callsite_id)
          ),
          'samples',
          'count',
          1
        ) AS profile
      FROM
        jetstream_sample s
        JOIN thread t on s.utid = t.utid
        JOIN process p on t.upid = p.upid
        --WHERE t.name LIKE "ThreadPoolForegroundWorker%"
    )
  )