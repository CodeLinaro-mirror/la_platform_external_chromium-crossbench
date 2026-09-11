// Copyright 2026 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const WEB_ROOT = resolve(__dirname, '..');
const REPO_ROOT = resolve(WEB_ROOT, '../..');
const PUBLIC_BIN = resolve(WEB_ROOT, 'public/bin');
const ANDROID_ARM64_BIN = resolve(PUBLIC_BIN, 'android/arm64');

const PERFETTO_VERSION = 'v58.2-add693d8b';
const PERFETTO_BASE_URL = `https://ui.perfetto.dev/${PERFETTO_VERSION}`;

async function downloadFile(url, destPath) {
  console.log(`Downloading ${url} -> ${destPath}...`);
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(
      `Failed to download ${url}: ` +
        `HTTP ${response.status} ${response.statusText}`
    );
  }
  const buffer = await response.arrayBuffer();
  writeFileSync(destPath, Buffer.from(buffer));
  console.log(
    `Saved ${destPath} (${(buffer.byteLength / 1024 / 1024).toFixed(2)} MB).`
  );
}

async function preparePerfettoWasm() {
  mkdirSync(PUBLIC_BIN, { recursive: true });

  const artifacts = [
    {
      url: `${PERFETTO_BASE_URL}/trace_processor.wasm`,
      filename: 'trace_processor.wasm',
    },
    {
      url: `${PERFETTO_BASE_URL}/trace_processor_memory64.wasm`,
      filename: 'trace_processor_memory64.wasm',
    },
    {
      url: `${PERFETTO_BASE_URL}/engine_bundle.js`,
      filename: 'trace_processor_engine.js',
    },
  ];

  for (const { url, filename } of artifacts) {
    const destPath = resolve(PUBLIC_BIN, filename);
    if (!existsSync(destPath)) {
      await downloadFile(url, destPath);
    } else {
      console.log(`${filename} already exists at ${destPath}`);
    }
  }
}

function buildWprAndroid() {
  mkdirSync(ANDROID_ARM64_BIN, { recursive: true });
  const wprDest = resolve(ANDROID_ARM64_BIN, 'wpr');

  if (existsSync(wprDest)) {
    console.log(`WPR binary already exists at ${wprDest}`);
    return;
  }

  const buildScript = resolve(
    REPO_ROOT,
    'third_party/webpagereplay/scripts/build.py'
  );
  if (!existsSync(buildScript)) {
    throw new Error(`WebPageReplay build script not found at ${buildScript}`);
  }

  console.log(`Building WPR binary for android/arm64 using ${buildScript}...`);
  const result = spawnSync(
    'vpython3',
    [
      buildScript,
      '--os',
      'android',
      '--arch',
      'arm64',
      '--out-dir',
      ANDROID_ARM64_BIN,
      '--binary',
      'wpr',
    ],
    {
      stdio: 'inherit',
      cwd: REPO_ROOT,
    }
  );

  if (result.error) {
    throw new Error(
      `Failed to execute WPR build script: ${result.error.message}`,
      { cause: result.error }
    );
  }

  if (result.status !== 0) {
    throw new Error(`Failed to build WPR binary (exit code ${result.status})`);
  }

  if (!existsSync(wprDest)) {
    throw new Error(`Expected WPR binary was not produced at ${wprDest}`);
  }
  console.log(`Built WPR binary successfully at ${wprDest}`);
}

async function main() {
  try {
    console.log('=== Preparing LoadLine Web Binaries ===');
    await preparePerfettoWasm();
    buildWprAndroid();
    console.log('=== All binaries successfully prepared ===');
  } catch (err) {
    console.error('ERROR: Failed to prepare binaries:', err);
    process.exit(1);
  }
}

main();
