// Copyright 2026 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

import {describe, expect, it} from 'vitest';

import {TraceProcessorWasmEngine} from '../src/trace_processor_wasm';

describe('TraceProcessorWasmEngine Unit Test', () => {
  it('initializes WASM engine, registers SQL module, and executes queries',
     async () => {
       const engine = new TraceProcessorWasmEngine();
       await engine.initialize();

       // Test basic query
       const res1 =
           engine.query('SELECT 42 AS answer, \'Crossbench WASM\' AS msg');
       expect(res1.columns).toEqual(['answer', 'msg']);
       expect(res1.rows).toEqual([[42, 'Crossbench WASM']]);

       // Test registering a SQL package / table
       engine.query(`
        CREATE PERFETTO TABLE test_loadline_table AS
        SELECT 'amazon_visual' AS metric, 123.45 AS value
        UNION ALL
        SELECT 'amazon_interactive' AS metric, 67.89 AS value;
      `);

       const res2 = engine.query(
           'SELECT metric, value FROM test_loadline_table ORDER BY metric');
       expect(res2.columns).toEqual(['metric', 'value']);
       expect(res2.rows).toEqual([
         ['amazon_interactive', 67.89],
         ['amazon_visual', 123.45],
       ]);
     },
     30000);

  it('supports synchronous query and trace parsing', async () => {
    const engine = new TraceProcessorWasmEngine();
    await engine.initialize();

    engine.reset();
    engine.appendTraceData(new Uint8Array([0x00]));
    engine.finalizeTraceData();

    const res = engine.query('SELECT \'sync_metric\' AS metric, 99.5 AS value');
    expect(res.columns).toEqual(['metric', 'value']);
    expect(res.rows).toEqual([['sync_metric', 99.5]]);

    // Test registering a SQL package via RPC
    engine.registerSqlPackage('ext', [
      {
        name: 'pkg_test',
        sql: `
            CREATE PERFETTO TABLE pkg_test_table AS
            SELECT 'ext_score' AS metric, 42.0 AS value;
          `,
      },
    ]);

    const pkgRes = engine.query(`
        INCLUDE PERFETTO MODULE ext.pkg_test;
        SELECT metric, value FROM pkg_test_table;
      `);
    expect(pkgRes.columns).toEqual(['metric', 'value']);
    expect(pkgRes.rows).toEqual([['ext_score', 42.0]]);
  }, 30000);
});
