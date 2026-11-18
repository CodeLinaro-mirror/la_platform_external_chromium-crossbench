// Copyright 2026 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

import * as crypto from 'node:crypto';
import * as fs from 'node:fs';
import * as path from 'node:path';
import {describe, expect, it, vi} from 'vitest';

import {PyodideRunner, WebAdbProxy} from '../src/pyodide_worker';

function getCrossbenchFilesFromDisk(): Record<string, string> {
  const repoRoot = path.resolve(__dirname, '../../..');
  const files: Record<string, string> = {};

  function scanDir(dirPath: string, prefix: string, recursive: boolean = true) {
    if (!fs.existsSync(dirPath))
      return;
    const entries = fs.readdirSync(dirPath, {withFileTypes: true});
    for (const entry of entries) {
      const fullPath = path.join(dirPath, entry.name);
      if (entry.isDirectory()) {
        if (recursive && entry.name !== '__pycache__' &&
            entry.name !== 'node_modules' && entry.name !== 'dist' &&
            entry.name !== '.git') {
          scanDir(fullPath, prefix);
        }
      } else {
        if (entry.name.endsWith('.png') || entry.name === 'stdout') {
          continue;
        }
        const relPath = path.relative(path.join(repoRoot, prefix), fullPath);
        const fsPath = '/' + prefix + '/' + relPath.split(path.sep).join('/');
        files[fsPath] = fs.readFileSync(fullPath, 'utf8');
      }
    }
  }

  scanDir(path.join(repoRoot, 'crossbench'), 'crossbench');
  scanDir(path.join(repoRoot, 'config'), 'config');
  scanDir(path.join(repoRoot, 'third_party/protoc'), 'third_party/protoc');
  scanDir(
      path.join(repoRoot, 'third_party/webpagereplay'),
      'third_party/webpagereplay', false);
  scanDir(
      path.join(repoRoot, 'third_party/webpagereplay/scripts'),
      'third_party/webpagereplay/scripts', false);
  scanDir(path.join(repoRoot, 'tools/protoc'), 'tools/protoc');
  files['/third_party/__init__.py'] = '';
  files['/tools/__init__.py'] = '';
  return files;
}

function mockSendCdpCommand(method: string, paramsJson?: string): string {
  if (method === 'Target.getTargets') {
    return JSON.stringify({
      targetInfos: [
        {
          targetId: 'tab123',
          type: 'page',
          title: 'Mock Page',
          url: 'about:blank',
          webSocketDebuggerUrl: 'ws://localhost:9222/devtools/page/tab123',
        },
      ],
    });
  }
  if (method === 'Page.navigate') {
    return JSON.stringify({frameId: 'frame123'});
  }
  if (method !== 'Runtime.evaluate') {
    return JSON.stringify({});
  }
  if (paramsJson && paramsJson.includes('window.benchmarkClient.metrics')) {
    return JSON.stringify({
      result: {
        type: 'string',
        value: JSON.stringify({
          'TodoMVC-JavaScript-ES5': {mean: 45.0},
          'TodoMVC-JavaScript-ES5/Adding100Items': {mean: 20.0},
          'Iteration-0-Total': {mean: 45.0},
          Geomean: {mean: 45.0},
          Score: {mean: 22.2},
        }),
      },
    });
  }
  if (paramsJson && paramsJson.includes('element_rect')) {
    return JSON.stringify({
      result: {
        type: 'object',
        value: {
          count: 1,
          device_pixel_ratio: 3,
          window_outer_width: 360,
          window_outer_height: 800,
          window_inner_width: 360,
          window_inner_height: 700,
          screen_width: 360,
          screen_height: 800,
          screen_avail_width: 360,
          screen_avail_height: 760,
          window_offset_x: 0,
          window_offset_y: 0,
          element_rect: {
            left: 0,
            top: 0,
            width: 360,
            height: 700,
          },
        },
      },
    });
  }
  return JSON.stringify({
    result: {type: 'boolean', value: true},
  });
}

describe('Pyodide Integration Test (Real WebAssembly)', () => {
  it('loads real Pyodide, mounts crossbench, runs loading story, ' +
         'and tests TraceProcessor probe',
     async () => {
       const encoder = new TextEncoder();
       const dummyWprArchive = encoder.encode('mock-wpr-archive');
       const dummyWprMd5B64 =
           crypto.createHash('md5').update(dummyWprArchive).digest('base64');
       const remoteFiles = new Set<string>(['/system/bin/perfetto']);
       let runnerRef: PyodideRunner|null = null;
       let nextPid = 200;
       const spawnedCmds = new Map<number, string>();
       const mockWebAdb: WebAdbProxy = {
         serial: 'mock-usb-device',
         shell: vi.fn().mockImplementation((cmd: string, input?: string) => {
           if (cmd.includes('getprop ro.build.version.release')) {
             return encoder.encode('14\n');
           }
           if (cmd.includes('getprop ro.build.version.sdk'))
             return encoder.encode('34\n');
           if (cmd.includes('getprop ro.product.model'))
             return encoder.encode('Pixel 8\n');
           if (cmd.includes('getprop ro.product.cpu.abi')) {
             return encoder.encode('arm64-v8a\n');
           }
           if (cmd.includes('getprop')) {
             return encoder.encode('[ro.build.version.release]: [14]\n');
           }
           if (cmd.includes('settings get global device_provisioned')) {
             return encoder.encode('1\n');
           }
           if (cmd.includes('get-current-user'))
             return encoder.encode('0\n');
           if (cmd.includes('list users')) {
             return encoder.encode('UserInfo{0:null:4c13} running\n');
           }
           if (cmd.includes('list packages')) {
             return encoder.encode(
                 'package:com.android.chrome\n' +
                 'package:com.google.android.apps.chrome\n');
           }
           if (cmd.includes('dumpsys package')) {
             return encoder.encode('versionName=120.0.6099.144\n');
           }
           if (cmd.includes('dumpsys window displays --proto')) {
             const repoRoot = path.resolve(__dirname, '../../..');
             const fileBuf = fs.readFileSync(path.join(
                 repoRoot, 'tests/crossbench/plt/pb/display/1080p.pb'));
             return new Uint8Array(
                 fileBuf.buffer, fileBuf.byteOffset, fileBuf.byteLength);
           }
           if (cmd.includes('dumpsys window')) {
             return encoder.encode('mAppBounds=Rect(0, 0 - 1080, 2400)\n');
           }
           if (cmd.includes('dumpsys power')) {
             return encoder.encode('mHoldingDisplaySuspendBlocker=true\n');
           }
           if (cmd.includes('dumpsys battery')) {
             return encoder.encode('level: 100\ntemperature: 250\n');
           }
           if (cmd.includes('uname -m'))
             return encoder.encode('aarch64\n');
           if (cmd.includes('which perfetto')) {
             return encoder.encode('/system/bin/perfetto\n');
           }
           if (cmd.includes('mktemp -d')) {
             return encoder.encode('/data/local/tmp/cb_wpr_tmp\n');
           }
           if (cmd.startsWith('perfetto --background')) {
             const outMatch = cmd.match(/--out\s+(\S+)/);
             if (outMatch) {
               remoteFiles.add(outMatch[1]);
             }
             return encoder.encode('9999\n');
           }
           if (cmd.includes('[ -f ') || cmd.includes('[ -e ')) {
             for (const rf of remoteFiles) {
               if (cmd.includes(rf)) {
                 return encoder.encode('1\n');
               }
             }
             return encoder.encode('');
           }
           if (cmd.includes('cat') && cmd.includes('chrome-command-line')) {
             return encoder.encode('');
           }
           if (cmd.includes('am set-debug-app'))
             return encoder.encode('Success\n');
           if (cmd.includes('am start')) {
             return encoder.encode(
                 'Starting: Intent { act=android.intent.action.VIEW ' +
                 'dat=about:blank pkg=com.android.chrome }\n');
           }
           if (cmd.includes('pm clear') || cmd.includes('am stop-app') ||
               cmd.includes('am force-stop')) {
             return encoder.encode('Success\n');
           }
           if (cmd.includes('tee /sys/kernel/tracing/trace_marker') && !input) {
             throw new Error(`Hanging tee command without stdin input: ${cmd}`);
           }
           return encoder.encode('');
         }),
         push: vi.fn().mockImplementation((_src: string, dest: string) => {
           remoteFiles.add(dest);
         }),
         pull: vi.fn().mockImplementation((_src: string, dest: string) => {
           if (runnerRef) {
             const pyFs = runnerRef.getFS();
             const dir = dest.substring(0, dest.lastIndexOf('/'));
             if (dir && !pyFs.analyzePath(dir).exists) {
               pyFs.mkdirTree(dir);
             }
             // Minimal valid Perfetto Trace proto (TracePacket { timestamp: 1
             // })
             pyFs.writeFile(dest, new Uint8Array([0x0a, 0x02, 0x08, 0x01]));
           }
         }),
         startDevTools: vi.fn().mockReturnValue('devtools-socket-1234'),
         stopDevTools: vi.fn().mockReturnValue('ok'),
         switchTab: vi.fn().mockReturnValue(
             'ws://localhost:9222/devtools/page/tab123'),
         sendCdpCommand: vi.fn().mockImplementation(mockSendCdpCommand),
         spawnProcess: vi.fn().mockImplementation((cmd: string) => {
           const pid = ++nextPid;
           spawnedCmds.set(pid, cmd);
           return pid;
         }),
         writeProcessStdin: vi.fn(),
         closeProcessStdin: vi.fn(),
         readProcessLog: vi.fn().mockImplementation((id: number) => {
           const cmd = spawnedCmds.get(id) || '';
           if (cmd.includes('wpr')) {
             return JSON.stringify({
               text: 'Starting server on http://127.0.0.1:8080\n' +
                   'Starting server on https://127.0.0.1:8443\n',
               nextOffset: 1,
               isExited: false,
               exitCode: null,
             });
           }
           return JSON.stringify({
             text: '',
             nextOffset: 0,
             isExited: false,
             exitCode: null,
           });
         }),
         killProcess: vi.fn(),
         gcsGetMetadata: vi.fn().mockReturnValue(JSON.stringify({
           name: 'archive_phone_20260331.wprgo',
           md5Hash: dummyWprMd5B64,
           size: dummyWprArchive.length,
         })),
       };

       const logs: string[] = [];
       const runner = new PyodideRunner(mockWebAdb, (msg) => {
         logs.push(msg);
       });
       runnerRef = runner;
       await runner.init();

       const pyFiles = getCrossbenchFilesFromDisk();
       expect(Object.keys(pyFiles).length).toBeGreaterThan(400);

       await runner.mountFiles(pyFiles);

       // Test running Crossbench CLI describe subcommand
       await runner.runCrossbench(['describe', 'loadline2-phone']);
       expect(logs.some((l) => l.includes('loadline2-phone'))).toBe(true);

       // Test running Crossbench loading benchmark with cdp:chrome
       await runner.runCrossbench([
         'loading',
         '--browser',
         'cdp:chrome',
         '--url',
         'https://www.google.com',
         '--env-validation=warn',
         '--fast',
         '--throw',
       ]);
       expect(mockWebAdb.shell).toHaveBeenCalled();
       expect(mockWebAdb.shell)
           .toHaveBeenCalledWith(
               'tee /sys/kernel/tracing/trace_marker',
               expect.stringContaining('crossbench-iteration-start'));
       expect(mockWebAdb.startDevTools).toHaveBeenCalled();
       expect(mockWebAdb.sendCdpCommand).toHaveBeenCalled();

       // Test full loadline2-phone benchmark execution (WPR + Perfetto +
       // TraceProcessor + LoadLine2Probe + ResultsDB)
       await runner.mountBinaryFile(
           '/cache/webpagereplay/android/arm64/wpr',
           encoder.encode('mock-wpr-bin'));
       const safeMd5 = await runner.runScript(`
from crossbench import path as pth
pth.safe_filename(${JSON.stringify(dummyWprMd5B64)})
`);
       await runner.mountBinaryFile(
           `/cache/wpr/archive_phone_20260331_${safeMd5}.wprgo`,
           dummyWprArchive);
       await runner.mountBinaryFile(
           `/cache/wpr/archive_speedometer_3.1_20261113_${safeMd5}.wprgo`,
           dummyWprArchive);
       await runner.runScript(
           'import time; _real_sleep = time.sleep; ' +
           'time.sleep = lambda s: None');
       try {
         await runner.runCrossbench([
           'loadline2-phone',
           '--browser',
           'cdp:chrome',
           '--repeat',
           '1',
           '--stories=amazon_product',
           '--throw',
         ]);
         await runner.runCrossbench([
           'speedometer_3.1',
           '--browser',
           'cdp:chrome',
           '--repeat',
           '1',
           '--stories=TodoMVC-JavaScript-ES5',
           '--network',
           JSON.stringify({
             type: 'wpr',
             url: 'gs://chrome-partner-loadline/' +
                 'archive_speedometer_3.1_20261113.wprgo',
             persist_server: true,
             run_on_device: true,
           }),
           '--throw',
         ]);
       } finally {
         await runner.runScript('time.sleep = _real_sleep');
       }
       expect(
           logs.some((l) => l.includes('Could not find llvm-symbolizer')),
           )
           .toBe(false);

       // Test Perfetto probe trace config serialization with real protobuf
       const perfettoTestScript = `
import google.protobuf.text_format as proto_text_format
from crossbench import path as pth
from crossbench.probes.cb_perfetto.perfetto import TraceConfig

cfg = TraceConfig.parse_path(
    pth.LocalPath('/config/probe/perfetto/trace_config/default.txtpb')
)
text = proto_text_format.MessageToString(cfg.trace_config)
assert isinstance(text, str) and len(text) > 0, (
    f"Expected str trace config, got {type(text)}"
)
"OK"
`;
       const perfettoRes = await runner.runScript(perfettoTestScript);
       expect(perfettoRes).toBe('OK');

       // Test uinput virtual device setup and event injection in Pyodide
       const uinputTestScript = `
from unittest import mock
from crossbench.action_runner.input_events import TouchEvent
from crossbench.action_runner.virtual_device.touchscreen import (
    TouchscreenVirtualDeviceConfig,
)
from crossbench.benchmarks.loading.point import Point
from crossbench.plt.pyodide_adb import PyodideAndroidAdbPlatform

plt = PyodideAndroidAdbPlatform()
with mock.patch.object(plt.adb, "getprop", return_value="37"), \\
     mock.patch.object(plt, "sleep"):
  plt.setup_virtual_devices(
      (TouchscreenVirtualDeviceConfig(name="touch1", width=1080, height=2400),)
  )
  plt.inject_input_events(
      "touch1",
      (
          TouchEvent(Point(100, 200), is_down=True),
          TouchEvent(Point(100, 200), is_down=False),
      ),
  )
"OK"
`;
       const uinputRes = await runner.runScript(uinputTestScript);
       expect(uinputRes).toBe('OK');
       expect(mockWebAdb.spawnProcess).toHaveBeenCalledWith('uinput -');
       const uinputPid = [...spawnedCmds.entries()]
                             .find(([, cmd]) => cmd === 'uinput -')
                             ?.[0];
       expect(uinputPid).toBeDefined();
       expect(mockWebAdb.writeProcessStdin)
           .toHaveBeenCalledWith(
               uinputPid, expect.stringContaining('N: touch1'));
       expect(mockWebAdb.writeProcessStdin)
           .toHaveBeenCalledWith(
               uinputPid, expect.stringContaining('0003 0035 0100'));

       // Test Perfetto TraceProcessor in Pyodide with real pandas, numpy, scipy
       const tpTestScript = `
import pandas as pd
import numpy as np
import scipy.stats
from perfetto.trace_processor.api import TraceProcessor

tp = TraceProcessor()
sql = (
    "SELECT 'amazon_product_visual' AS metric, 100.0 AS value, "
    "'browser_1' AS cb_browser, 0 AS cb_run UNION ALL "
    "SELECT 'amazon_product_interactive' AS metric, 200.0 AS value, "
    "'browser_1' AS cb_browser, 0 AS cb_run"
)
df = tp.query(sql).as_pandas_dataframe()
assert isinstance(df, pd.DataFrame), f"Expected DataFrame, got {type(df)}"
assert len(df) == 2, f"Expected 2 rows, got {len(df)}"
assert list(df['metric']) == [
    'amazon_product_visual',
    'amazon_product_interactive',
]

# Test including ext.loadline2_score SQL module registered via
# TPM_REGISTER_SQL_PACKAGE
ext_sql = (
    "INCLUDE PERFETTO MODULE ext.loadline2_score; "
    "SELECT * FROM loadline2_score;"
)
ext_df = tp.query(ext_sql).as_pandas_dataframe()
assert isinstance(ext_df, pd.DataFrame)
assert list(ext_df.columns) == ['metric', 'value']

# Test TraceProcessor with trace parsing then query
tp_with_trace = TraceProcessor(trace="/dev/null")
trace_df = tp_with_trace.query(ext_sql).as_pandas_dataframe()
assert isinstance(trace_df, pd.DataFrame)

# Test non-existent trace raises FileNotFoundError
try:
    TraceProcessor(trace="/nonexistent_trace.perfetto-trace")
    assert False, "Expected FileNotFoundError for non-existent trace"
except FileNotFoundError:
    pass

# Test trace_summary and metric serialization
summary = tp.trace_summary()
assert hasattr(summary, "SerializeToString")
assert isinstance(summary.SerializeToString(), bytes)

from google.protobuf.json_format import MessageToJson
m = tp.metric(["trace_metadata"])
assert isinstance(MessageToJson(m), str)

# Test LoadLine 2 score processing with real scipy.stats
from crossbench.benchmarks.loadline.loadline_2 import process_scores
scores_df = process_scores(df, expected_metrics=2)
assert isinstance(scores_df, pd.DataFrame)
assert not scores_df.empty

# Test tabulate on scores DataFrame
from tabulate import tabulate
tab_str = tabulate(scores_df.reset_index(), headers="keys", tablefmt="plain")
assert "Metric" in tab_str
assert "TOTAL_SCORE" in tab_str
assert "browser_1" in tab_str
"OK"
`;
       const tpRes = await runner.runScript(tpTestScript);
       expect(tpRes).toBe('OK');

       // Test exporting results zip
       const zipBytes = await runner.exportResultsZip();
       expect(zipBytes).toBeInstanceOf(Uint8Array);
       expect(zipBytes.length).toBeGreaterThan(0);
       // Standard zip magic number is PK\x03\x04 (0x50, 0x4b, 0x03, 0x04)
       expect(zipBytes[0]).toBe(0x50);
       expect(zipBytes[1]).toBe(0x4b);

       // Test Speedometer 3.1 score CSV extraction from speedometer_3.1.json
       await runner.runScript(`
import json, os
os.makedirs("/results/sp_run", exist_ok=True)
with open("/results/sp_run/speedometer_3.1.json", "w") as f:
    json.dump({
        "cdp_chrome": {
            "info": {"label": "cdp_chrome"},
            "data": {
                "TodoMVC-JavaScript-ES5": {"average": 45.0, "stddev": 0.0},
                "TodoMVC-JavaScript-ES5/Adding100Items": {
                    "average": 20.0,
                    "stddev": 0.0,
                },
                "Iteration-0-Total": {"average": 45.0, "stddev": 0.0},
                "Geomean": {"average": 45.0, "stddev": 0.0},
                "Score": {"average": 22.2, "stddev": 0.0},
            },
        }
    }, f)
`);
       const spCsv = await runner.getBenchmarkScoreCsv('/results/sp_run');
       expect(spCsv).toContain('Metric,cdp_chrome');
       expect(spCsv).toContain('TodoMVC-JavaScript-ES5,');
       expect(spCsv).not.toContain('Adding100Items');
       expect(spCsv).not.toContain('Iteration-0-Total');
       expect(spCsv).not.toContain('Geomean');
       expect(spCsv).toContain('Score,');
     },
     60000);
});
