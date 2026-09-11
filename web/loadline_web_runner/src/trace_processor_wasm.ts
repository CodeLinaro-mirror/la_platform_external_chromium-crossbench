// Copyright 2026 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

/**
 * WebAssembly Perfetto Trace Processor client and RPC codec.
 * Runs in-browser or Node.js Web Workers without external dependencies.
 */

export function encodeVarint(val: number): number[] {
  const bytes: number[] = [];
  let v = Math.floor(val);
  while (v >= 0x80) {
    bytes.push((v & 0x7f) | 0x80);
    v = Math.floor(v / 128);
  }
  bytes.push(v & 0x7f);
  return bytes;
}

export class ProtoWriter {
  private chunks: Uint8Array[] = [];

  writeTag(fieldNum: number, wireType: number): void {
    this.chunks.push(new Uint8Array(encodeVarint((fieldNum << 3) | wireType)));
  }

  writeVarintField(fieldNum: number, val: number): void {
    this.writeTag(fieldNum, 0);
    this.chunks.push(new Uint8Array(encodeVarint(val)));
  }

  writeBytesField(fieldNum: number, data: Uint8Array): void {
    this.writeTag(fieldNum, 2);
    this.chunks.push(new Uint8Array(encodeVarint(data.length)));
    this.chunks.push(data);
  }

  writeStringField(fieldNum: number, str: string): void {
    const encoded = new TextEncoder().encode(str);
    this.writeBytesField(fieldNum, encoded);
  }

  writeNestedMessage(fieldNum: number, writer: ProtoWriter): void {
    const data = writer.finish();
    this.writeBytesField(fieldNum, data);
  }

  finish(): Uint8Array {
    let totalLen = 0;
    for (const c of this.chunks)
      totalLen += c.length;
    const res = new Uint8Array(totalLen);
    let offset = 0;
    for (const c of this.chunks) {
      res.set(c, offset);
      offset += c.length;
    }
    return res;
  }
}

export class ProtoReader {
  public buf: Uint8Array;
  public pos = 0;

  constructor(buf: Uint8Array|ArrayBuffer) {
    this.buf = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
  }

  hasMore(): boolean {
    return this.pos < this.buf.length;
  }

  readVarint(): number {
    let res = 0;
    let shift = 0;
    while (this.pos < this.buf.length) {
      const b = this.buf[this.pos++];
      res += (b & 0x7f) * (2 ** shift);
      if (!(b & 0x80))
        break;
      shift += 7;
    }
    return res;
  }

  readTag(): {fieldNum: number; wireType: number}|null {
    if (!this.hasMore())
      return null;
    const tag = this.readVarint();
    return {fieldNum: tag >>> 3, wireType: tag & 7};
  }

  readBytes(): Uint8Array {
    const len = this.readVarint();
    const sub = this.buf.subarray(this.pos, this.pos + len);
    this.pos += len;
    return sub;
  }

  readString(): string {
    return new TextDecoder().decode(this.readBytes());
  }

  readFloat64(): number {
    const view =
        new DataView(this.buf.buffer, this.buf.byteOffset + this.pos, 8);
    this.pos += 8;
    return view.getFloat64(0, true);
  }

  skip(wireType: number): void {
    if (wireType === 0) {
      this.readVarint();
    } else if (wireType === 1) {
      this.pos += 8;
    } else if (wireType === 2) {
      const len = this.readVarint();
      this.pos += len;
    } else if (wireType === 5) {
      this.pos += 4;
    } else {
      throw new Error(`Unsupported protobuf wire type: ${wireType}`);
    }
  }
}

export interface QueryResultData {
  columns: string[];
  rows: any[][];
  error?: string;
}

export function decodeQueryResult(bytes: Uint8Array): QueryResultData {
  const reader = new ProtoReader(bytes);
  const columns: string[] = [];
  let error: string|undefined = undefined;
  const batches: Array<{
    cells: number[]; varintCells: number[]; float64Cells: number[];
    blobCells: Uint8Array[];
    stringCells: string;
    isLastBatch: boolean;
  }> = [];

  while (reader.hasMore()) {
    const tag = reader.readTag();
    if (!tag)
      break;
    if (tag.fieldNum === 1) {
      columns.push(reader.readString());
    } else if (tag.fieldNum === 2) {
      error = reader.readString();
    } else if (tag.fieldNum === 3) {
      const batchBytes = reader.readBytes();
      const bReader = new ProtoReader(batchBytes);
      const batch = {
        cells: [] as number[],
        varintCells: [] as number[],
        float64Cells: [] as number[],
        blobCells: [] as Uint8Array[],
        stringCells: '',
        isLastBatch: false,
      };
      while (bReader.hasMore()) {
        const bTag = bReader.readTag();
        if (!bTag)
          break;
        if (bTag.fieldNum === 1) {
          const cellsLen = bReader.readVarint();
          const endPos = bReader.pos + cellsLen;
          while (bReader.pos < endPos) {
            batch.cells.push(bReader.readVarint());
          }
        } else if (bTag.fieldNum === 2) {
          const vLen = bReader.readVarint();
          const endPos = bReader.pos + vLen;
          while (bReader.pos < endPos) {
            batch.varintCells.push(bReader.readVarint());
          }
        } else if (bTag.fieldNum === 3) {
          const fLen = bReader.readVarint();
          const endPos = bReader.pos + fLen;
          while (bReader.pos < endPos) {
            batch.float64Cells.push(bReader.readFloat64());
          }
        } else if (bTag.fieldNum === 4) {
          batch.blobCells.push(bReader.readBytes());
        } else if (bTag.fieldNum === 5) {
          batch.stringCells = bReader.readString();
        } else if (bTag.fieldNum === 6) {
          batch.isLastBatch = Boolean(bReader.readVarint());
        } else {
          bReader.skip(bTag.wireType);
        }
      }
      batches.push(batch);
    } else {
      reader.skip(tag.wireType);
    }
  }

  if (error) {
    return {columns: [], rows: [], error};
  }

  const rows: any[][] = [];
  const colCount = columns.length;
  let currentRow: any[] = [];

  for (const batch of batches) {
    const stringList = batch.stringCells ? batch.stringCells.split('\0') : [];
    let vIdx = 0;
    let fIdx = 0;
    let sIdx = 0;
    let bIdx = 0;
    for (const cellType of batch.cells) {
      let val: any = null;
      if (cellType === 1) {
        val = null;
      } else if (cellType === 2) {
        val = batch.varintCells[vIdx++];
      } else if (cellType === 3) {
        val = batch.float64Cells[fIdx++];
      } else if (cellType === 4) {
        val = stringList[sIdx++];
      } else if (cellType === 5) {
        val = batch.blobCells[bIdx++];
      }
      currentRow.push(val);
      if (currentRow.length === colCount) {
        rows.push(currentRow);
        currentRow = [];
      }
    }
  }

  return {columns, rows};
}

export class TraceProcessorWasmEngine {
  private seq = 1;
  private bridge: any = null;
  private lastSyncResponse: any = null;
  private isInitialized = false;

  async initialize(
      wasmModuleOrBytes?: WebAssembly.Module|Uint8Array,
      engineJsCode?: string): Promise<void> {
    if (this.isInitialized)
      return;

    let wasmModule: WebAssembly.Module;
    if (wasmModuleOrBytes instanceof WebAssembly.Module) {
      wasmModule = wasmModuleOrBytes;
    } else if (wasmModuleOrBytes instanceof Uint8Array) {
      wasmModule = await WebAssembly.compile(
          wasmModuleOrBytes as unknown as ArrayBuffer);
    } else {
      let wasmBytes: Uint8Array;
      const isNode =
          typeof process !== 'undefined' && process.versions?.node != null;
      if (isNode) {
        const fs = await import('node:fs');
        const path = await import('node:path');
        const {fileURLToPath} = await import('node:url');
        const currentDir = path.dirname(fileURLToPath(import.meta.url));
        const candidate =
            path.resolve(currentDir, '../public/bin/trace_processor.wasm');
        if (!fs.existsSync(candidate)) {
          throw new Error(`trace_processor.wasm not found at ${candidate}`);
        }
        wasmBytes = new Uint8Array(fs.readFileSync(candidate));
      } else if (typeof fetch !== 'undefined') {
        const resp = await fetch('/bin/trace_processor.wasm');
        if (!resp.ok) {
          throw new Error(
              'Failed to fetch /bin/trace_processor.wasm: ' +
              `HTTP ${resp.status} ${resp.statusText}`);
        }
        wasmBytes = new Uint8Array(await resp.arrayBuffer());
      } else {
        throw new Error(
            'Could not load trace_processor.wasm: unsupported environment');
      }
      wasmModule =
          await WebAssembly.compile(wasmBytes as unknown as ArrayBuffer);
    }

    let code = engineJsCode || '';
    if (!code) {
      const isNode =
          typeof process !== 'undefined' && process.versions?.node != null;
      if (isNode) {
        const fs = await import('node:fs');
        const path = await import('node:path');
        const {fileURLToPath} = await import('node:url');
        const currentDir = path.dirname(fileURLToPath(import.meta.url));
        const candidate =
            path.resolve(currentDir, '../public/bin/trace_processor_engine.js');
        if (!fs.existsSync(candidate)) {
          throw new Error(
              `trace_processor_engine.js not found at ${candidate}`);
        }
        code = fs.readFileSync(candidate, 'utf8');
      } else if (typeof fetch !== 'undefined') {
        const resp = await fetch('/bin/trace_processor_engine.js');
        if (!resp.ok) {
          throw new Error(
              'Failed to fetch /bin/trace_processor_engine.js: ' +
              `HTTP ${resp.status} ${resp.statusText}`);
        }
        code = await resp.text();
      } else {
        throw new Error(
            'Could not load trace_processor_engine.js: ' +
            'unsupported environment');
      }
    }

    const mockPort = {
      postMessage: (data: any) => {
        const bytes = data instanceof Uint8Array ? data : new Uint8Array(data);
        this.handleRpcResponse(bytes);
      },
    };

    const mockSelf: any = {
      location: typeof location !== 'undefined' ? location :
                                                  {href: 'http://localhost/'},
      importScripts: () => {},
      onmessage: null as any,
      WorkerGlobalScope: true,
    };

    let patchedCode =
        code.replace(
                /function memory64Supported\(\)\s*\{/g,
                () => 'function memory64Supported() { return false;')
            .replace(
                /var wasmBridge = new WasmBridge\(\);/g,
                () => 'var wasmBridge = self.wasmBridge = new WasmBridge();')
            .replace(
                /\$ENVIRONMENT_IS_WEB\$\$ = !!globalThis\.window/g,
                () => '$ENVIRONMENT_IS_WEB$$ = false')
            .replace(
                new RegExp(
                    '\\$ENVIRONMENT_IS_NODE\\$\\$ = ' +
                        'globalThis\\.\\$g\\$\\?\\.\\$versions\\$\\?\\.node',
                    'g'),
                () => '$ENVIRONMENT_IS_NODE$$ = false')
            .replace(
                new RegExp(
                    '\\$ENVIRONMENT_IS_WORKER\\$\\$ = ' +
                        '!!globalThis\\.WorkerGlobalScope',
                    'g'),
                () => '$ENVIRONMENT_IS_WORKER$$ = true');

    const fn = new Function('self', 'location', patchedCode);
    fn(mockSelf, mockSelf.location);

    if (mockSelf.wasmBridge &&
        typeof mockSelf.wasmBridge.initialize === 'function') {
      await mockSelf.wasmBridge.initialize(mockPort, wasmModule);
      this.bridge = mockSelf.wasmBridge;
    } else {
      throw new Error('TraceProcessor WASM bridge could not be initialized');
    }

    this.isInitialized = true;
  }

  private handleRpcResponse(streamBytes: Uint8Array): void {
    const streamReader = new ProtoReader(streamBytes);
    while (streamReader.hasMore()) {
      const tag = streamReader.readTag();
      if (!tag || tag.fieldNum !== 1)
        break;
      const rpcBytes = streamReader.readBytes();
      const rpcReader = new ProtoReader(rpcBytes);

      let fatalError: string|undefined;
      let queryResultBytes: Uint8Array|undefined;
      let metricResultBytes: Uint8Array|undefined;
      let appendResultBytes: Uint8Array|undefined;

      while (rpcReader.hasMore()) {
        const rTag = rpcReader.readTag();
        if (!rTag)
          break;
        if (rTag.fieldNum === 1) {
          rpcReader.readVarint();
        } else if (rTag.fieldNum === 3) {
          rpcReader.readVarint();
        } else if (rTag.fieldNum === 5) {
          fatalError = rpcReader.readString();
        } else if (rTag.fieldNum === 201) {
          appendResultBytes = rpcReader.readBytes();
        } else if (rTag.fieldNum === 203) {
          queryResultBytes = rpcReader.readBytes();
        } else if (rTag.fieldNum === 205) {
          metricResultBytes = rpcReader.readBytes();
        } else {
          rpcReader.skip(rTag.wireType);
        }
      }

      let parsedResult: any = null;
      if (fatalError) {
        parsedResult = new Error(`TraceProcessor fatal error: ${fatalError}`);
      } else if (queryResultBytes) {
        parsedResult = decodeQueryResult(queryResultBytes);
      } else if (metricResultBytes) {
        parsedResult = metricResultBytes;
      } else {
        parsedResult = appendResultBytes || null;
      }

      if (queryResultBytes && this.lastSyncResponse &&
          typeof this.lastSyncResponse === 'object' &&
          !(this.lastSyncResponse instanceof Error) &&
          Array.isArray(this.lastSyncResponse.rows)) {
        if (parsedResult.columns && parsedResult.columns.length > 0 &&
            (!this.lastSyncResponse.columns ||
             this.lastSyncResponse.columns.length === 0)) {
          this.lastSyncResponse.columns = parsedResult.columns;
        }
        if (parsedResult.rows && parsedResult.rows.length > 0) {
          this.lastSyncResponse.rows.push(...parsedResult.rows);
        }
        if (parsedResult.error) {
          this.lastSyncResponse.error = parsedResult.error;
        }
      } else {
        this.lastSyncResponse = parsedResult;
      }
    }
  }

  private encodeRpcRequest(
      typeVal: number, argsField?: number,
      argsBytes?: Uint8Array): {reqSeq: number; streamBytes: Uint8Array} {
    const reqSeq = this.seq++;

    const rpcWriter = new ProtoWriter();
    rpcWriter.writeVarintField(1, reqSeq);   // seq
    rpcWriter.writeVarintField(2, typeVal);  // request type

    if (argsField && argsBytes) {
      rpcWriter.writeBytesField(argsField, argsBytes);
    }

    const rpcBytes = rpcWriter.finish();

    const streamWriter = new ProtoWriter();
    streamWriter.writeBytesField(1, rpcBytes);
    const streamBytes = streamWriter.finish();

    return {reqSeq, streamBytes};
  }

  private sendRpcRequestSync(
      typeVal: number, argsField?: number, argsBytes?: Uint8Array): any {
    const {streamBytes} = this.encodeRpcRequest(typeVal, argsField, argsBytes);
    this.lastSyncResponse = null;

    if (this.bridge && typeof this.bridge.onMessage === 'function') {
      this.bridge.onMessage({data: streamBytes});
    }
    const res = this.lastSyncResponse;
    if (res instanceof Error) {
      throw res;
    }
    return res;
  }

  reset(): void {
    this.sendRpcRequestSync(11);  // TPM_RESET_TRACE_PROCESSOR = 11
  }

  appendTraceData(chunk: Uint8Array): void {
    // TPM_APPEND_TRACE_DATA = 1, field 101
    this.sendRpcRequestSync(1, 101, chunk);
  }

  finalizeTraceData(): void {
    this.sendRpcRequestSync(2);  // TPM_FINALIZE_TRACE_DATA = 2
  }

  query(sql: string): QueryResultData {
    const qWriter = new ProtoWriter();
    qWriter.writeStringField(1, sql);
    const qBytes = qWriter.finish();
    const res = this.sendRpcRequestSync(3, 103, qBytes);
    if (!res) {
      throw new Error('TraceProcessor query returned no response');
    }
    if (res.error) {
      throw new Error(`TraceProcessor query error: ${res.error}`);
    }
    return res;
  }

  registerSqlPackage(
      packageName: string, modules: Array<{name: string; sql: string}>): void {
    const pkgWriter = new ProtoWriter();
    pkgWriter.writeStringField(1, packageName);
    for (const mod of modules) {
      const modWriter = new ProtoWriter();
      const fullName = mod.name.startsWith(`${packageName}.`) ?
          mod.name :
          `${packageName}.${mod.name}`;
      modWriter.writeStringField(1, fullName);
      modWriter.writeStringField(2, mod.sql);
      pkgWriter.writeNestedMessage(2, modWriter);
    }
    pkgWriter.writeVarintField(3, 1);
    const pkgBytes = pkgWriter.finish();
    this.sendRpcRequestSync(13, 108, pkgBytes);
  }

  computeMetric(metrics: string[]): Uint8Array {
    const mWriter = new ProtoWriter();
    for (const m of metrics) {
      mWriter.writeStringField(1, m);
    }
    const mBytes = mWriter.finish();
    return this.sendRpcRequestSync(5, 105, mBytes);
  }
}
