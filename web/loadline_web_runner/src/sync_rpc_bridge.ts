// Copyright 2026 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

/**
 * Synchronous ADB RPC bridge over SharedArrayBuffer & Atomics between
 * Pyodide worker and browser main thread.
 */

export interface WebAdbProxy {
  serial?: string;
  shell(cmd: string): Uint8Array|string;
  push(src: string, dest: string): void;
  pull(src: string, dest: string): void;
  startDevTools?(): string;
  stopDevTools?(): string;
  switchTab?(url?: string): string;
  sendCdpCommand?(method: string, paramsJson: string): string;
  spawnProcess?(cmd: string): number;
  readProcessLog?(id: number, offset: number): string;
  killProcess?(id: number): void;
  gcsGetMetadata?(url: string): string;
  gcsDownloadFile?(url: string, dest: string): void;
}

export class SynchronousWorkerAdbBridge implements WebAdbProxy {
  serial?: string;
  private sab: SharedArrayBuffer|null = null;
  private getFs?: () => any;
  private interruptBuffer: Uint8Array|null = null;
  private stopFlag: Int32Array|null = null;
  private pendingInterrupt: boolean = false;
  private wasInterruptedFlag: boolean = false;

  constructor(
      serial: string = 'webusb-device',
      getFs?: () => any,
      interruptBuffer?: Uint8Array|null,
      stopFlag?: Int32Array|null,
  ) {
    this.serial = serial;
    this.getFs = getFs;
    this.interruptBuffer = interruptBuffer || null;
    this.stopFlag = stopFlag || null;
    if (!this.stopFlag && this.interruptBuffer &&
        this.interruptBuffer.buffer.byteLength >= 8) {
      try {
        this.stopFlag = new Int32Array(this.interruptBuffer.buffer, 4, 1);
      } catch {
        this.stopFlag = null;
      }
    }
    if (typeof SharedArrayBuffer !== 'undefined') {
      try {
        this.sab = new SharedArrayBuffer(16 * 1024 * 1024);
      } catch {
        this.sab = null;
      }
    }
  }

  setInterruptBuffer(buf: Uint8Array|null, stopFlag?: Int32Array|null): void {
    this.interruptBuffer = buf;
    if (stopFlag !== undefined) {
      this.stopFlag = stopFlag;
    } else if (buf && buf.buffer.byteLength >= 8) {
      try {
        this.stopFlag = new Int32Array(buf.buffer, 4, 1);
      } catch {
        this.stopFlag = null;
      }
    }
  }

  isInterrupted(): boolean {
    return Boolean(
        (this.interruptBuffer && this.interruptBuffer[0] === 2) ||
        this.pendingInterrupt);
  }

  wasInterrupted(): boolean {
    return Boolean(
        (this.stopFlag && Atomics.load(this.stopFlag, 0) === 1) ||
        this.wasInterruptedFlag);
  }

  private consumeInterruptSignal(): boolean {
    if ((this.interruptBuffer && this.interruptBuffer[0] === 2) ||
        this.pendingInterrupt) {
      if (this.interruptBuffer) {
        this.interruptBuffer[0] = 0;
      }
      this.pendingInterrupt = false;
      this.wasInterruptedFlag = true;
      return true;
    }
    return false;
  }

  acknowledgeInterrupt(): void {
    if (this.interruptBuffer) {
      this.interruptBuffer[0] = 0;
    }
    this.pendingInterrupt = false;
    this.wasInterruptedFlag = true;
  }

  interrupt(): void {
    if (this.stopFlag) {
      Atomics.store(this.stopFlag, 0, 1);
    }
    if (this.interruptBuffer) {
      this.interruptBuffer[0] = 2;
    }
    this.pendingInterrupt = true;
    this.wasInterruptedFlag = true;
  }

  clearInterrupt(): void {
    this.pendingInterrupt = false;
    this.wasInterruptedFlag = false;
    if (this.stopFlag) {
      Atomics.store(this.stopFlag, 0, 0);
    }
    if (this.interruptBuffer) {
      this.interruptBuffer[0] = 0;
    }
  }

  setFs(getFs: () => any): void {
    this.getFs = getFs;
  }

  private callSyncRpcRaw(method: string, args: any[]):
      {status: number; bytes: Uint8Array} {
    if (this.consumeInterruptSignal()) {
      throw new Error('BenchmarkExecutionInterrupted: Stopped by user');
    }
    if (!this.sab || typeof Atomics === 'undefined') {
      throw new Error(
          'Synchronous communication requires SharedArrayBuffer and Atomics, ' +
          'which are unavailable or failed to allocate in this environment.');
    }

    const int32View = new Int32Array(this.sab);
    const uint8View = new Uint8Array(this.sab);
    int32View[0] = 0;  // 0 = waiting
    int32View[1] = 0;

    self.postMessage({
      type: 'SYNC_RPC_REQUEST',
      method,
      args,
      sab: this.sab,
    });

    while (int32View[0] === 0) {
      Atomics.wait(int32View, 0, 0, 100);
      if (this.consumeInterruptSignal()) {
        throw new Error('BenchmarkExecutionInterrupted: Stopped by user');
      }
    }

    if (this.consumeInterruptSignal()) {
      throw new Error('BenchmarkExecutionInterrupted: Stopped by user');
    }

    const status = int32View[0];
    const length = int32View[1];
    const responseBytes = uint8View.slice(8, 8 + length);
    return {status, bytes: responseBytes};
  }

  private callSyncRpc(method: string, args: any[]): string {
    const {status, bytes} = this.callSyncRpcRaw(method, args);
    const responseText = new TextDecoder().decode(bytes);
    if (status === 2) {
      throw new Error(`ADB sync RPC error (${method}): ${responseText}`);
    }
    return responseText;
  }

  shell(cmd: string): Uint8Array {
    const {status, bytes} = this.callSyncRpcRaw('shell', [cmd]);
    if (status === 2) {
      const errText = new TextDecoder().decode(bytes);
      throw new Error(`ADB sync RPC error (shell): ${errText}`);
    }
    return bytes;
  }

  push(src: string, dest: string): void {
    if (!this.getFs) {
      throw new Error('Pyodide FS getter is not set on ADB bridge');
    }
    const fs = this.getFs();
    const fileBytes: Uint8Array = fs.readFile(src, {encoding: 'binary'});
    const {status, bytes: errBytes} = this.callSyncRpcRaw('push', [
      src,
      dest,
      fileBytes,
    ]);
    if (status === 2) {
      const errText = new TextDecoder().decode(errBytes);
      throw new Error(`ADB sync RPC error (push): ${errText}`);
    }
  }

  pull(src: string, dest: string): void {
    if (!this.getFs) {
      throw new Error('Pyodide FS getter is not set on ADB bridge');
    }
    const {status, bytes} = this.callSyncRpcRaw('pull', [src, dest]);
    if (status === 2) {
      const errText = new TextDecoder().decode(bytes);
      throw new Error(`ADB sync RPC error (pull): ${errText}`);
    }
    const fs = this.getFs();
    const dir = dest.substring(0, dest.lastIndexOf('/'));
    if (dir) {
      if (!fs.analyzePath || !fs.analyzePath(dir).exists) {
        try {
          fs.mkdirTree(dir);
        } catch (err: any) {
          if (err?.code !== 'EEXIST') {
            throw err;
          }
        }
      }
    }
    fs.writeFile(dest, bytes);
  }

  startDevTools(): string {
    return this.callSyncRpc('startDevTools', []);
  }

  stopDevTools(): string {
    return this.callSyncRpc('stopDevTools', []);
  }

  switchTab(url: string = 'about:blank'): string {
    return this.callSyncRpc('switchTab', [url]);
  }

  sendCdpCommand(method: string, paramsJson: string): string {
    return this.callSyncRpc('sendCdpCommand', [method, paramsJson]);
  }

  spawnProcess(cmd: string): number {
    const res = this.callSyncRpc('spawnProcess', [cmd]);
    const pid = parseInt(res, 10);
    if (isNaN(pid)) {
      throw new Error(
          `Failed to parse process PID from spawnProcess response: "${res}"`);
    }
    return pid;
  }

  readProcessLog(id: number, offset: number): string {
    return this.callSyncRpc('readProcessLog', [id, offset]);
  }

  killProcess(id: number): void {
    this.callSyncRpc('killProcess', [id]);
  }

  gcsGetMetadata(url: string): string {
    return this.callSyncRpc('gcsGetMetadata', [url]);
  }

  gcsDownloadFile(url: string, dest: string): void {
    if (!this.getFs) {
      throw new Error('Pyodide FS getter is not set on ADB bridge');
    }
    const {status, bytes} = this.callSyncRpcRaw('gcsDownloadFile', [
      url,
      dest,
    ]);
    if (status === 2) {
      const errText = new TextDecoder().decode(bytes);
      throw new Error(`GCS download sync RPC error: ${errText}`);
    }
    const fs = this.getFs();
    const dir = dest.substring(0, dest.lastIndexOf('/'));
    if (dir) {
      if (!fs.analyzePath || !fs.analyzePath(dir).exists) {
        try {
          fs.mkdirTree(dir);
        } catch (err: any) {
          if (err?.code !== 'EEXIST') {
            throw err;
          }
        }
      }
    }
    fs.writeFile(dest, bytes);
  }
}
