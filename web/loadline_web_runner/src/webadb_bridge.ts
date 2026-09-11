// Copyright 2026 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

/**
 * WebADB Socket Bridge for Android USB Communication.
 *
 * Manages WebUSB connections to Android devices to establish raw socket streams
 * to localabstract domain sockets like `localabstract:chrome_devtools_remote`,
 * execute shell commands, push/pull files, and spawn background processes.
 */

import {Adb, type AdbCredentialStore, AdbDaemonTransport,} from '@yume-chan/adb';
import {ADB_DEFAULT_DEVICE_FILTER, AdbWebUsbBackend,} from '@yume-chan/adb-backend-webusb';

import {DevToolsSocketStream, WebAdbSocketStream,} from './devtools_discovery';
import {WebAdbCredentialStore,} from './webadb_crypto';

export * from './webadb_crypto';
export * from './devtools_discovery';

/**
 * Checks if the WebUSB API is supported by the current browser environment.
 */
export function isWebUsbSupported(): boolean {
  return (
      typeof navigator !== 'undefined' && 'usb' in navigator &&
      Boolean(navigator.usb));
}

/**
 * WebAdbBridge manages USB discovery and ADB connection to Android devices.
 */
export class WebAdbBridge {
  private adbInstance: Adb|null = null;
  private backend: AdbWebUsbBackend|null = null;
  private credentialStore: AdbCredentialStore;

  constructor(credentialStore?: AdbCredentialStore) {
    this.credentialStore = credentialStore || new WebAdbCredentialStore();
  }

  get isConnected(): boolean {
    return this.adbInstance !== null;
  }

  get serial(): string|null {
    return this.adbInstance?.serial ?? null;
  }

  /**
   * Prompts the user to select an Android USB device using WebUSB API.
   */
  async requestDevice(): Promise<AdbWebUsbBackend|null> {
    if (!isWebUsbSupported()) {
      throw new Error(
          'WebUSB API is not supported in this browser. Please use a browser ' +
          'with WebUSB support (e.g. Google Chrome).');
    }
    const device = await navigator.usb.requestDevice({
      filters: [ADB_DEFAULT_DEVICE_FILTER],
    });
    if (!device) {
      return null;
    }
    this.backend = new AdbWebUsbBackend(
        device, [ADB_DEFAULT_DEVICE_FILTER], navigator.usb);
    return this.backend;
  }

  /**
   * Connects to the provided or requested WebUSB backend using @yume-chan/adb.
   */
  async connect(backend?: AdbWebUsbBackend): Promise<void> {
    const activeBackend = backend || this.backend;
    if (!activeBackend) {
      throw new Error('No USB device backend provided or selected.');
    }
    this.backend = activeBackend;
    const connection = await this.backend.connect();

    console.log(
        `[WebADB] Connecting to ${activeBackend.serial || 'usb-device'} ` +
        'with RSA authentication...');
    const transport = await AdbDaemonTransport.authenticate({
      serial: activeBackend.serial || 'usb-device',
      connection: connection as any,
      credentialStore: this.credentialStore,
    });
    console.log(
        `[WebADB] Authenticated successfully. Banner device: ` +
        `"${transport.banner.device || 'N/A'}", Features: ` +
        JSON.stringify(transport.clientFeatures));
    this.adbInstance = new Adb(transport);
  }

  /**
   * Creates a stream socket to Chrome DevTools
   * (default: `localabstract:chrome_devtools_remote`).
   */
  async createDevToolsSocket(
      socketName: string = 'localabstract:chrome_devtools_remote'):
      Promise<DevToolsSocketStream> {
    if (!this.adbInstance) {
      throw new Error('ADB device is not connected. Call connect() first.');
    }
    const socket = await this.adbInstance.createSocket(socketName);
    return new WebAdbSocketStream(
        socket.readable as unknown as ReadableStream<Uint8Array>,
        socket.writable as unknown as WritableStream<Uint8Array>, async () => {
          await socket.close();
        });
  }

  /**
   * Queries Chrome DevTools HTTP /json/version endpoint to discover browser
   * WebSocket URL.
   */
  async getDevToolsVersion(
      socketName: string = 'localabstract:chrome_devtools_remote'):
      Promise<{webSocketDebuggerUrl?: string; [key: string]: any}> {
    if (!this.adbInstance) {
      throw new Error('ADB device is not connected. Call connect() first.');
    }
    const stream = await this.createDevToolsSocket(socketName);

    try {
      const requestText = 'GET /json/version HTTP/1.1\r\n' +
          'Host: localhost\r\n' +
          'Connection: close\r\n\r\n';
      await stream.write(new TextEncoder().encode(requestText));

      const decoder = new TextDecoder();
      let responseText = '';

      const readWithTimeout = async(): Promise<Uint8Array|null> => {
        let timerId: ReturnType<typeof setTimeout>|undefined;
        try {
          const timeoutPromise = new Promise<null>((resolve) => {
            timerId = setTimeout(() => resolve(null), 1500);
          });
          return await Promise.race([stream.read(), timeoutPromise]);
        } finally {
          if (timerId !== undefined) {
            clearTimeout(timerId);
          }
        }
      };

      while (true) {
        const chunk = await readWithTimeout();
        if (!chunk) {
          break;
        }
        responseText += decoder.decode(chunk, {stream: true});
        const idx = responseText.indexOf('\r\n\r\n');
        if (idx !== -1) {
          const bodyText = responseText.slice(idx + 4).trim();
          if (bodyText.startsWith('{') && bodyText.endsWith('}')) {
            break;
          }
        }
      }
      responseText += decoder.decode();

      const headerEndIndex = responseText.indexOf('\r\n\r\n');
      if (headerEndIndex === -1) {
        throw new Error(
            `Invalid HTTP response from ${socketName} /json/version: ` +
            'header end not found');
      }
      const bodyText = responseText.slice(headerEndIndex + 4).trim();
      if (!bodyText) {
        throw new Error(
            `Empty HTTP response body from ${socketName} /json/version`);
      }
      try {
        return JSON.parse(bodyText);
      } catch {
        throw new Error(
            `Failed to parse DevTools version JSON from ${socketName}. ` +
            `Body: ${bodyText.slice(0, 100)}`);
      }
    } finally {
      await stream.close();
    }
  }

  /**
   * Discovers active Chrome/Webview DevTools abstract sockets on Android.
   */
  async discoverDevToolsSocket(): Promise<string> {
    const unixSocketsBytes = await this.shell('cat /proc/net/unix');
    const unixSockets = new TextDecoder().decode(unixSocketsBytes);
    const lines = unixSockets.split('\n');
    for (const line of lines) {
      const match = line.match(/@(chrome_devtools_remote(?:_\d+)?)/);
      if (match) {
        return `localabstract:${match[1]}`;
      }
    }
    throw new Error(
        'No Chrome DevTools socket found in /proc/net/unix. ' +
        'Ensure Chrome is running on the device with debugging enabled.');
  }

  /**
   * Executes a shell command on the connected Android device via ADB
   * subprocess service and returns raw binary bytes without text
   * decoding/mangling.
   */
  async shell(cmd: string): Promise<Uint8Array> {
    if (!this.adbInstance) {
      throw new Error('ADB device is not connected. Call connect() first.');
    }
    const service = this.adbInstance.subprocess.shellProtocol ||
        this.adbInstance.subprocess.noneProtocol;
    const output = await service.spawnWait(cmd);
    if (output instanceof Uint8Array) {
      return output;
    }
    if ((output as any)?.stdout instanceof Uint8Array) {
      return (output as any).stdout;
    }
    throw new Error(
        `Unexpected output format from ADB shell command "${cmd}": ` +
        'expected Uint8Array or object with stdout Uint8Array, ' +
        `received ${typeof output}`);
  }

  /**
   * Pushes a file to the Android device as binary bytes using ADB sync service.
   */
  async push(remotePath: string, data: Uint8Array): Promise<void> {
    if (!this.adbInstance) {
      throw new Error('ADB device is not connected. Call connect() first.');
    }
    const parentDir = remotePath.substring(0, remotePath.lastIndexOf('/'));
    if (parentDir) {
      await this.shell(`mkdir -p ${parentDir}`);
    }
    const sync = await this.adbInstance.sync();
    try {
      const fileStream = new ReadableStream<Uint8Array>({
        start(controller) {
          controller.enqueue(data);
          controller.close();
        },
      });
      await sync.write({
        filename: remotePath,
        file: fileStream as any,
        permission: 0o755,
      });
    } finally {
      await sync.dispose();
    }
  }

  /**
   * Pulls a file from the Android device as binary bytes using ADB sync
   * service.
   */
  async pull(remotePath: string): Promise<Uint8Array> {
    if (!this.adbInstance) {
      throw new Error('ADB device is not connected. Call connect() first.');
    }
    const sync = await this.adbInstance.sync();
    try {
      const stream = sync.read(remotePath);
      const reader = stream.getReader();
      const chunks: Uint8Array[] = [];
      let totalLen = 0;
      while (true) {
        const {done, value} = await reader.read();
        if (done)
          break;
        if (value) {
          chunks.push(value);
          totalLen += value.length;
        }
      }
      const result = new Uint8Array(totalLen);
      let offset = 0;
      for (const chunk of chunks) {
        result.set(chunk, offset);
        offset += chunk.length;
      }
      return result;
    } finally {
      await sync.dispose();
    }
  }

  private nextProcessId = 1;
  private activeProcesses = new Map < number, {
    id: number;
    cmd: string;
    process: any;
    logText: string;
    isExited: boolean;
    exitCode: number|null;
  }
  >();

  /**
   * Spawns a long-running streaming background process over ADB.
   * Keeps the ADB stream alive and buffers stdout/stderr until terminated.
   */
  async spawnProcess(cmd: string): Promise<number> {
    if (!this.adbInstance) {
      throw new Error('ADB device is not connected. Call connect() first.');
    }
    console.log(`[WebADB Spawn] Starting streaming process: ${cmd}`);
    const service = this.adbInstance.subprocess.shellProtocol ||
        this.adbInstance.subprocess.noneProtocol;
    const proc = await service.spawn(cmd);
    const procId = this.nextProcessId++;
    const activeProc = {
      id: procId,
      cmd,
      process: proc,
      logText: '',
      isExited: false,
      exitCode: null as number | null,
    };
    this.activeProcesses.set(procId, activeProc);

    const readStream = async (stream: ReadableStream<Uint8Array>) => {
      const decoder = new TextDecoder();
      try {
        const reader = stream.getReader();
        while (true) {
          const {done, value} = await reader.read();
          if (done)
            break;
          if (value && value.length > 0) {
            const chunkStr = decoder.decode(value, {stream: true});
            activeProc.logText += chunkStr;
          }
        }
        const remaining = decoder.decode();
        if (remaining) {
          activeProc.logText += remaining;
        }
      } catch (err) {
        console.warn(`[WebADB Process #${procId}] Stream reader error:`, err);
      }
    };

    if ((activeProc.process as any).stdout) {
      readStream((activeProc.process as any).stdout);
    }
    if ((activeProc.process as any).stderr) {
      readStream((activeProc.process as any).stderr);
    }
    if ((activeProc.process as any).output) {
      readStream((activeProc.process as any).output);
    }

    if (proc.exited) {
      proc.exited.then(
          (code: any) => {
            activeProc.isExited = true;
            activeProc.exitCode = typeof code === 'number' ? code : 0;
          },
          (err: any) => {
            activeProc.isExited = true;
            activeProc.exitCode = 1;
            console.warn(`[WebADB Process #${procId}] Exited with error:`, err);
          });
    }

    return procId;
  }

  /**
   * Reads new buffered log output from a spawned process.
   */
  readProcessLog(procId: number, offset: number): {
    text: string; nextOffset: number; isExited: boolean;
    exitCode: number | null;
  } {
    const activeProc = this.activeProcesses.get(procId);
    if (!activeProc) {
      throw new Error(`Process #${procId} not found in active processes.`);
    }
    const currentLen = activeProc.logText.length;
    const newText = currentLen > offset ? activeProc.logText.slice(offset) : '';
    return {
      text: newText,
      nextOffset: currentLen,
      isExited: activeProc.isExited,
      exitCode: activeProc.exitCode,
    };
  }

  /**
   * Terminates a spawned background process and closes its ADB stream.
   */
  async killProcess(procId: number): Promise<void> {
    const activeProc = this.activeProcesses.get(procId);
    if (!activeProc) {
      throw new Error(`Process #${procId} not found in active processes.`);
    }
    try {
      console.log(
          `[WebADB Kill] Terminating process #${procId} (${activeProc.cmd})`);
      if (typeof (activeProc.process as any)?.kill === 'function') {
        await (activeProc.process as any).kill();
      }
    } finally {
      this.activeProcesses.delete(procId);
    }
  }

  /**
   * Disconnects the current ADB session and closes USB backend.
   */
  async disconnect(): Promise<void> {
    try {
      for (const procId of Array.from(this.activeProcesses.keys())) {
        await this.killProcess(procId);
      }
    } finally {
      if (this.adbInstance) {
        await this.adbInstance.close();
        this.adbInstance = null;
      }
      this.backend = null;
    }
  }
}
