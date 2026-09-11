// Copyright 2026 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

import {AdbDaemonTransport} from '@yume-chan/adb';
import {beforeEach, describe, expect, it, vi} from 'vitest';

import {getBrowserUpgradePath, isWebUsbSupported, WebAdbBridge, WebAdbCredentialStore, WebAdbSocketStream,} from '../src/webadb_bridge';

describe('WebAdbCredentialStore', () => {
  it('generates valid RSA-2048 private key in PKCS#8 format', async () => {
    const store = new WebAdbCredentialStore();
    const key = await store.generateKey();
    expect(key.buffer).toBeInstanceOf(Uint8Array);
    expect(key.buffer.length).toBeGreaterThan(1000);
    expect(key.name).toBe('crossbench@web');

    const iteratedKeys: any[] = [];
    for await (const k of store.iterateKeys()) {
      iteratedKeys.push(k);
    }
    expect(iteratedKeys.length).toBeGreaterThanOrEqual(1);
    expect(iteratedKeys[0].name).toBe('crossbench@web');
  });

  it('provides new iterator on each iterateKeys call', async () => {
    const store = new WebAdbCredentialStore();
    await store.generateKey();
    const iter1 = store.iterateKeys();
    const iter2 = store.iterateKeys();
    expect(iter1).not.toBe(iter2);
  });
});

describe('WebAdbSocketStream', () => {
  it('reads and writes Uint8Array chunks to streams and closes cleanly',
     async () => {
       const writtenChunks: Uint8Array[] = [];
       const readable = new ReadableStream<Uint8Array>({
         start(controller) {
           controller.enqueue(new Uint8Array([10, 20, 30]));
           controller.close();
         },
       });

       const writable = new WritableStream<Uint8Array>({
         write(chunk) {
           writtenChunks.push(chunk);
         },
       });

       const closeSpy = vi.fn().mockResolvedValue(undefined);
       const socketStream =
           new WebAdbSocketStream(readable, writable, closeSpy);

       const readData = await socketStream.read();
       expect(readData).toEqual(new Uint8Array([10, 20, 30]));

       const eofData = await socketStream.read();
       expect(eofData).toBeNull();

       await socketStream.write(new Uint8Array([40, 50]));
       expect(writtenChunks.length).toBe(1);
       expect(writtenChunks[0]).toEqual(new Uint8Array([40, 50]));

       await socketStream.close();
       expect(closeSpy).toHaveBeenCalled();
     });
});

describe('WebAdbBridge Integration & WebUSB Mock', () => {
  let bridge: WebAdbBridge;

  beforeEach(() => {
    bridge = new WebAdbBridge();
  });

  it('initializes in disconnected state', () => {
    expect(bridge.isConnected).toBe(false);
    expect(bridge.serial).toBeNull();
  });

  it('detects WebUSB API support via isWebUsbSupported helper', () => {
    const originalNavigator = globalThis.navigator;

    // Supported environment
    Object.defineProperty(globalThis, 'navigator', {
      value: {usb: {}},
      configurable: true,
      writable: true,
    });
    expect(isWebUsbSupported()).toBe(true);

    // Unsupported environment (no usb property)
    Object.defineProperty(globalThis, 'navigator', {
      value: {},
      configurable: true,
      writable: true,
    });
    expect(isWebUsbSupported()).toBe(false);

    // Unsupported environment (null/undefined navigator)
    // @ts-ignore
    delete (globalThis as any).navigator;
    expect(isWebUsbSupported()).toBe(false);

    Object.defineProperty(globalThis, 'navigator', {
      value: originalNavigator,
      configurable: true,
      writable: true,
    });
  });

  it('throws error when requesting device without WebUSB support', async () => {
    const originalNavigator = globalThis.navigator;
    // @ts-ignore
    delete globalThis.navigator;

    const errorRegex = new RegExp(
        'WebUSB API is not supported in this browser. ' +
        'Please use a browser with WebUSB support');
    await expect(bridge.requestDevice()).rejects.toThrow(errorRegex);

    globalThis.navigator = originalNavigator;
  });

  it('connects to mock USB backend with authenticate', async () => {
    const mockTransport = {
      serial: 'mock-serial-123',
      banner: {device: 'Pixel 10 Pro', raw: 'device::'},
      clientFeatures: [],
      disconnected: new Promise(() => {}),
      connect: vi.fn(),
      close: vi.fn().mockResolvedValue(undefined),
    };
    const authSpy = vi.spyOn(AdbDaemonTransport, 'authenticate')
                        .mockResolvedValue(mockTransport as any);

    const mockConnection = {
      readable: new ReadableStream({
        start(c) {
          c.close();
        },
      }),
      writable: new WritableStream({write() {}}),
    };

    const mockBackend = {
      serial: 'mock-serial-123',
      connect: vi.fn().mockResolvedValue(mockConnection),
    };

    // @ts-ignore
    await bridge.connect(mockBackend);
    expect(authSpy).toHaveBeenCalledWith(expect.objectContaining({
      serial: 'mock-serial-123',
      connection: mockConnection,
      credentialStore: expect.any(WebAdbCredentialStore),
    }));
    expect(bridge.isConnected).toBe(true);
    expect(bridge.serial).toBe('mock-serial-123');

    const pullData = new Uint8Array([10, 20, 30, 40]);
    // @ts-ignore
    bridge.adbInstance = {
      sync: vi.fn().mockResolvedValue({
        read: vi.fn().mockReturnValue(new ReadableStream({
          start(c) {
            c.enqueue(pullData);
            c.close();
          },
        })),
        dispose: vi.fn().mockResolvedValue(undefined),
      }),
      close: vi.fn().mockResolvedValue(undefined),
    };

    const result = await bridge.pull('/data/misc/test.trace');
    expect(result).toEqual(pullData);

    await bridge.disconnect();
    expect(bridge.isConnected).toBe(false);
  });
});

describe('WebAdbBridge operations', () => {
  let bridge: any;

  beforeEach(() => {
    bridge = new WebAdbBridge();
    bridge.adbInstance = {
      subprocess: {
        shellProtocol: {
          spawnWait: vi.fn().mockResolvedValue(new Uint8Array(0)),
          spawn: vi.fn(),
        },
        noneProtocol: {
          spawnWait: vi.fn().mockResolvedValue(new Uint8Array(0)),
          spawn: vi.fn(),
        },
      },
      sync: vi.fn(),
      close: vi.fn(),
    } as any;
  });

  it('runs shell command with Uint8Array output', async () => {
    bridge.adbInstance.subprocess.shellProtocol.spawnWait.mockResolvedValue(
        new Uint8Array([1, 2, 3]));
    const result = await bridge.shell('ls');
    expect(result).toEqual(new Uint8Array([1, 2, 3]));
  });

  it('runs shell command with stdout Uint8Array output', async () => {
    bridge.adbInstance.subprocess.shellProtocol.spawnWait.mockResolvedValue({
      stdout: new Uint8Array([1, 2, 3]),
    });
    const result = await bridge.shell('ls');
    expect(result).toEqual(new Uint8Array([1, 2, 3]));
  });

  it('shell throws error when output format is unexpected', async () => {
    bridge.adbInstance.subprocess.shellProtocol.spawnWait.mockResolvedValue(
        'invalid-output');
    await expect(bridge.shell('echo test'))
        .rejects.toThrow(
            'Unexpected output format from ADB shell command "echo test"');
  });

  it('push() uses ADB sync', async () => {
    const mockSync = {
      write: vi.fn().mockResolvedValue(undefined),
      dispose: vi.fn().mockResolvedValue(undefined),
    };
    bridge.adbInstance.sync.mockResolvedValue(mockSync);

    await bridge.push('/data/local/tmp/test.txt', new Uint8Array([4, 5, 6]));
    expect(mockSync.write).toHaveBeenCalled();
    expect(mockSync.dispose).toHaveBeenCalled();
  });

  it('push() propagates sync failure, no fallback', async () => {
    const mockSync = {
      write: vi.fn().mockRejectedValue(new Error('Sync error')),
      dispose: vi.fn().mockResolvedValue(undefined),
    };
    bridge.adbInstance.sync.mockResolvedValue(mockSync);
    bridge.shell = vi.fn();

    const pushPromise =
        bridge.push('/data/local/tmp/test.txt', new Uint8Array([4, 5, 6]));
    await expect(pushPromise).rejects.toThrow('Sync error');
    expect(bridge.shell).toHaveBeenCalledTimes(1);
  });

  it('pull() propagates sync failure, no fallback', async () => {
    const mockSync = {
      read: vi.fn().mockImplementation(() => {
        throw new Error('Sync error read');
      }),
      dispose: vi.fn().mockResolvedValue(undefined),
    };
    bridge.adbInstance.sync.mockResolvedValue(mockSync);
    bridge.shell = vi.fn();

    const pullPromise = bridge.pull('/data/local/tmp/test.txt');
    await expect(pullPromise).rejects.toThrow('Sync error read');
    expect(bridge.shell).not.toHaveBeenCalled();
  });

  it('discoverDevToolsSocket reads /proc/net/unix', async () => {
    const output = '0000000: 00000002 0 @chrome_devtools_remote_12345\n';
    bridge.shell = vi.fn().mockResolvedValue(new TextEncoder().encode(output));
    const sock = await bridge.discoverDevToolsSocket();
    expect(sock).toBe('localabstract:chrome_devtools_remote_12345');
  });

  it('discoverDevToolsSocket throws error when no socket matches', async () => {
    const output = '0000000: 00000002 0 @some_other_socket\n';
    bridge.shell = vi.fn().mockResolvedValue(new TextEncoder().encode(output));
    await expect(bridge.discoverDevToolsSocket())
        .rejects.toThrow('No Chrome DevTools socket found in /proc/net/unix');
  });

  it('spawnProcess, readProcessLog, killProcess', async () => {
    const procMock = {
      stdout: new ReadableStream({
        start(c) {
          c.enqueue(new TextEncoder().encode('hello '));
          c.enqueue(new TextEncoder().encode('world'));
          c.close();
        },
      }),
      kill: vi.fn().mockResolvedValue(undefined),
      exited: Promise.resolve(0),
    };
    const shellProto = bridge.adbInstance.subprocess.shellProtocol;
    shellProto.spawn.mockResolvedValue(procMock);

    const procId = await bridge.spawnProcess('top');
    expect(procId).toBe(1);

    // Flush microtasks to allow stream reading
    for (let i = 0; i < 5; i++) {
      await Promise.resolve();
    }

    const log1 = bridge.readProcessLog(1, 0);
    expect(log1.text).toBe('hello world');
    expect(log1.nextOffset).toBe(11);

    await bridge.killProcess(1);
    expect(procMock.kill).toHaveBeenCalled();
  });

  it('readProcessLog throws error when procId is not found', () => {
    expect(() => bridge.readProcessLog(999, 0))
        .toThrow('Process #999 not found in active processes.');
  });

  it('killProcess throws error when procId is not found', async () => {
    await expect(bridge.killProcess(999))
        .rejects.toThrow('Process #999 not found in active processes.');
  });
});

describe('WebAdbBridge getDevToolsVersion', () => {
  let bridge: WebAdbBridge;

  beforeEach(() => {
    bridge = new WebAdbBridge();
  });

  it('queries DevTools /json/version and parses response', async () => {
    const jsonBody = JSON.stringify({
      Browser: 'Chrome/120.0.0.0',
      'Protocol-Version': '1.3',
      webSocketDebuggerUrl: 'ws://127.0.0.1:9222/devtools/browser/abc',
    });
    const httpResponse = `HTTP/1.1 200 OK\r\n` +
        `Content-Length: ${jsonBody.length}\r\n` +
        `Content-Type: application/json; charset=UTF-8\r\n\r\n` + jsonBody;

    const mockSocketStream = {
      write: vi.fn().mockResolvedValue(undefined),
      read: vi.fn()
                .mockResolvedValueOnce(new TextEncoder().encode(httpResponse))
                .mockResolvedValue(null),
      close: vi.fn().mockResolvedValue(undefined),
    };

    bridge.createDevToolsSocket =
        vi.fn().mockResolvedValue(mockSocketStream as any);
    (bridge as any).adbInstance = {} as any;

    const version = await bridge.getDevToolsVersion();
    expect(version.Browser).toBe('Chrome/120.0.0.0');
    expect(version.webSocketDebuggerUrl)
        .toBe('ws://127.0.0.1:9222/devtools/browser/abc');
    expect(mockSocketStream.close).toHaveBeenCalled();
  });

  it('throws error when response header is invalid and ensures stream closes',
     async () => {
       const mockSocketStream = {
         write: vi.fn().mockResolvedValue(undefined),
         read: vi.fn()
                   .mockResolvedValueOnce(
                       new TextEncoder().encode('invalid-payload'))
                   .mockResolvedValue(null),
         close: vi.fn().mockResolvedValue(undefined),
       };

       bridge.createDevToolsSocket =
           vi.fn().mockResolvedValue(mockSocketStream as any);
       (bridge as any).adbInstance = {} as any;

       await expect(bridge.getDevToolsVersion())
           .rejects.toThrow(
               'Invalid HTTP response from ' +
               'localabstract:chrome_devtools_remote /json/version: ' +
               'header end not found');
       expect(mockSocketStream.close).toHaveBeenCalled();
     });

  it('throws error when response JSON is invalid', async () => {
    const httpResponse = 'HTTP/1.1 200 OK\r\n\r\n{invalid_json';
    const mockSocketStream = {
      write: vi.fn().mockResolvedValue(undefined),
      read: vi.fn()
                .mockResolvedValueOnce(new TextEncoder().encode(httpResponse))
                .mockResolvedValue(null),
      close: vi.fn().mockResolvedValue(undefined),
    };

    bridge.createDevToolsSocket =
        vi.fn().mockResolvedValue(mockSocketStream as any);
    (bridge as any).adbInstance = {} as any;

    await expect(bridge.getDevToolsVersion())
        .rejects.toThrow('Failed to parse DevTools version JSON');
    expect(mockSocketStream.close).toHaveBeenCalled();
  });
});

describe('getBrowserUpgradePath', () => {
  it('extracts path when webSocketDebuggerUrl is valid', () => {
    const url = 'ws://localhost/devtools/browser/abc';
    expect(getBrowserUpgradePath({
      webSocketDebuggerUrl: url
    })).toBe('/devtools/browser/abc');
  });

  it('throws error when webSocketDebuggerUrl is missing or invalid', () => {
    expect(() => getBrowserUpgradePath({}))
        .toThrow('Missing webSocketDebuggerUrl');
    expect(() => getBrowserUpgradePath(undefined))
        .toThrow('Missing webSocketDebuggerUrl');
    expect(() => getBrowserUpgradePath({
             webSocketDebuggerUrl: 'ws://localhost/devtools/page/123',
           }))
        .toThrow('does not contain "/devtools/browser"');
  });
});
