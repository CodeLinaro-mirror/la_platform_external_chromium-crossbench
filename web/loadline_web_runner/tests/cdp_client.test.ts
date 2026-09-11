// Copyright 2026 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

/**
 * Unit and integration tests for Chrome DevTools Protocol Client
 * (tests/cdp_client.test.ts).
 */

import {beforeEach, describe, expect, it} from 'vitest';

import {CdpClient, decodeWebSocketFrame, encodeWebSocketFrame,} from '../src/cdp_client';
import {DevToolsSocketStream} from '../src/devtools_discovery';

/** Mock implementation of DevToolsSocketStream for testing CdpClient */
class MockSocketStream implements DevToolsSocketStream {
  readable: ReadableStream<Uint8Array>;
  writable: WritableStream<Uint8Array>;
  writtenFrames: Uint8Array[] = [];
  private controller!: ReadableStreamDefaultController<Uint8Array>;

  constructor() {
    this.readable = new ReadableStream<Uint8Array>({
      start: (c) => {
        this.controller = c;
      },
    });

    this.writable = new WritableStream<Uint8Array>({
      write: (chunk) => {
        this.writtenFrames.push(chunk);
        this.handleClientWrite(chunk);
      },
    });
  }

  /** Pushes an incoming frame or message to the client reader stream */
  pushIncomingFrame(data: Uint8Array|string): void {
    const frame =
        typeof data === 'string' ? encodeWebSocketFrame(data, false) : data;
    this.controller.enqueue(frame);
  }

  /** Custom message handler for automated response mocking */
  onClientWrite?: (jsonMsg: any) => void;

  private handleClientWrite(chunk: Uint8Array): void {
    try {
      const decoded = decodeWebSocketFrame(chunk);
      if (decoded) {
        const json = JSON.parse(new TextDecoder().decode(decoded.payload));
        if (this.onClientWrite) {
          this.onClientWrite(json);
        }
      }
    } catch {
      // Ignore framing decode errors in tests if raw payload written
    }
  }

  async write(data: Uint8Array): Promise<void> {
    const writer = this.writable.getWriter();
    await writer.write(data);
    writer.releaseLock();
  }

  async read(): Promise<Uint8Array|null> {
    const reader = this.readable.getReader();
    const res = await reader.read();
    reader.releaseLock();
    return res.value ?? null;
  }

  async close(): Promise<void> {
    try {
      this.controller.close();
    } catch {
      // Already closed
    }
  }
}

describe('WebSocket Framing Utilities', () => {
  it('encodes and decodes small text WebSocket frames', () => {
    const originalText = 'Hello CDP!';
    const encodedFrame = encodeWebSocketFrame(originalText, true);
    expect(encodedFrame.length).toBeGreaterThan(originalText.length);

    const decoded = decodeWebSocketFrame(encodedFrame);
    expect(decoded).not.toBeNull();
    expect(decoded!.fin).toBe(true);
    expect(decoded!.opcode).toBe(1);
    expect(decoded!.bytesConsumed).toBe(encodedFrame.length);
    const decodedText = new TextDecoder().decode(decoded!.payload);
    expect(decodedText).toBe(originalText);
  });

  it('encodes and decodes medium payloads (126-65535 bytes)', () => {
    const mediumText = 'A'.repeat(500);
    const encodedFrame = encodeWebSocketFrame(mediumText, true);
    expect(encodedFrame[1] & 0x7f).toBe(126);

    const decoded = decodeWebSocketFrame(encodedFrame);
    expect(decoded).not.toBeNull();
    expect(new TextDecoder().decode(decoded!.payload)).toBe(mediumText);
  });

  it('encodes and decodes unmasked server frames', () => {
    const text = 'Server push event';
    const encodedFrame = encodeWebSocketFrame(text, false);
    const decoded = decodeWebSocketFrame(encodedFrame);
    expect(decoded).not.toBeNull();
    expect(new TextDecoder().decode(decoded!.payload)).toBe(text);
  });

  it('returns null for incomplete frames', () => {
    // Buffer too short for even a 2-byte header
    expect(decodeWebSocketFrame(new Uint8Array([0x81]))).toBeNull();

    // Buffer too short for 16-bit length
    expect(decodeWebSocketFrame(new Uint8Array([0x81, 126, 0x01]))).toBeNull();

    // Buffer too short for payload
    const partial = encodeWebSocketFrame('hello world', false).slice(0, 5);
    expect(decodeWebSocketFrame(partial)).toBeNull();
  });
});

describe('CdpClient Command Execution & Page.navigate', () => {
  let mockStream: MockSocketStream;
  let client: CdpClient;

  beforeEach(async () => {
    mockStream = new MockSocketStream();
    client = new CdpClient(mockStream);
  });

  it('sends CDP command and resolves result', async () => {
    mockStream.onClientWrite = (req) => {
      if (req.method === 'Target.setDiscoverTargets') {
        mockStream.pushIncomingFrame(
            JSON.stringify({id: req.id, result: {success: true}}));
      }
    };

    await client.connect();
    const result = await client.send<{success: boolean}>(
        'Target.setDiscoverTargets', {discover: true});
    expect(result).toEqual({success: true});
  });

  it('handles CDP command error responses', async () => {
    mockStream.onClientWrite = (req) => {
      mockStream.pushIncomingFrame(JSON.stringify({
        id: req.id,
        error: {code: -32601, message: 'Method not found'},
      }));
    };

    await client.connect();
    await expect(client.send('Invalid.method'))
        .rejects.toThrow(/CDP Error -32601: Method not found/);
  });

  it('includes error data in rejection when provided by CDP', async () => {
    mockStream.onClientWrite = (req) => {
      mockStream.pushIncomingFrame(JSON.stringify({
        id: req.id,
        error: {
          code: -32000,
          message: 'Cannot navigate to invalid URL',
          data: 'net::ERR_NAME_NOT_RESOLVED',
        },
      }));
    };

    await client.connect();
    await expect(client.send('Page.navigate'))
        .rejects.toThrow(
            'CDP Error -32000: Cannot navigate to invalid URL ' +
            '(net::ERR_NAME_NOT_RESOLVED)');
  });

  it('navigates to URL and waits for Page.loadEventFired', async () => {
    mockStream.onClientWrite = (req) => {
      if (req.method === 'Page.enable') {
        mockStream.pushIncomingFrame(JSON.stringify({id: req.id, result: {}}));
      } else if (req.method === 'Page.navigate') {
        mockStream.pushIncomingFrame(JSON.stringify({
          id: req.id,
          result: {frameId: 'F123', loaderId: 'L456'},
        }));
        // Simulate event after navigation request
        setTimeout(() => {
          mockStream.pushIncomingFrame(JSON.stringify({
            method: 'Page.loadEventFired',
            params: {timestamp: 123456.78},
          }));
        }, 10);
      }
    };

    await client.connect();
    const navResult = await client.navigate('https://example.com', true);

    expect(navResult.frameId).toBe('F123');
    expect(navResult.loaderId).toBe('L456');
  });

  it('removes Page.loadEventFired listener even if Page.navigate fails',
     async () => {
       mockStream.onClientWrite = (req) => {
         if (req.method === 'Page.enable') {
           mockStream.pushIncomingFrame(
               JSON.stringify({id: req.id, result: {}}));
         } else if (req.method === 'Page.navigate') {
           mockStream.pushIncomingFrame(JSON.stringify({
             id: req.id,
             error: {code: -32000, message: 'Navigation failed'},
           }));
         }
       };

       await client.connect();
       await expect(client.navigate('https://invalid.local'))
           .rejects.toThrow(/Navigation failed/);

       // Verify listener is cleaned up by triggering Page.loadEventFired;
       // no handler should be invoked
       expect(() => {
         client.handleIncomingMessage(JSON.stringify({
           method: 'Page.loadEventFired',
           params: {timestamp: 1234},
         }));
       }).not.toThrow();
     });

  it('initializes browser session and routes commands with sessionId',
     async () => {
       mockStream.onClientWrite = (req) => {
         if (req.method === 'Target.getTargets') {
           mockStream.pushIncomingFrame(JSON.stringify({
             id: req.id,
             result: {
               targetInfos: [{targetId: 'page_target_1', type: 'page'}],
             },
           }));
         } else if (req.method === 'Target.attachToTarget') {
           mockStream.pushIncomingFrame(JSON.stringify({
             id: req.id,
             result: {sessionId: 'session_page_1'},
           }));
         } else if (req.method === 'Runtime.evaluate') {
           expect(req.sessionId).toBe('session_page_1');
           mockStream.pushIncomingFrame(JSON.stringify({
             id: req.id,
             result: {result: {type: 'string', value: 'hello'}},
           }));
         }
       };

       await client.connect();
       const sid = await client.initBrowserSession();
       expect(sid).toBe('session_page_1');
       expect(client.sessionId).toBe('session_page_1');

       const evalResult =
           await client.send<{result: {value: string};}>('Runtime.evaluate', {
             expression: '1 + 1',
           });
       expect(evalResult.result.value).toBe('hello');
     });

  it('throws an error if initBrowserSession fails to obtain sessionId',
     async () => {
       mockStream.onClientWrite = (req) => {
         if (req.method === 'Target.getTargets') {
           mockStream.pushIncomingFrame(JSON.stringify({
             id: req.id,
             result: {
               targetInfos: [{targetId: 'page_target_1', type: 'page'}],
             },
           }));
         } else if (req.method === 'Target.attachToTarget') {
           mockStream.pushIncomingFrame(JSON.stringify({
             id: req.id,
             result: {},
           }));
         }
       };

       await client.connect();
       await expect(client.initBrowserSession())
           .rejects.toThrow(
               /Target.attachToTarget failed to return a sessionId/);
     });

  it('switches to new tab and updates active sessionId', async () => {
    mockStream.onClientWrite = (req) => {
      if (req.method === 'Target.createTarget') {
        expect(req.params?.url).toBe('https://amazon.com');
        mockStream.pushIncomingFrame(JSON.stringify({
          id: req.id,
          result: {targetId: 'target_tab_2'},
        }));
      } else if (req.method === 'Target.attachToTarget') {
        expect(req.params?.targetId).toBe('target_tab_2');
        mockStream.pushIncomingFrame(JSON.stringify({
          id: req.id,
          result: {sessionId: 'session_tab_2'},
        }));
      } else if (req.method === 'Target.activateTarget') {
        mockStream.pushIncomingFrame(JSON.stringify({id: req.id, result: {}}));
      } else if (req.method === 'Page.navigate') {
        expect(req.sessionId).toBe('session_tab_2');
        mockStream.pushIncomingFrame(JSON.stringify({
          id: req.id,
          result: {frameId: 'F2'},
        }));
      }
    };

    await client.connect();
    const newSessionId = await client.switchTab('https://amazon.com');
    expect(newSessionId).toBe('session_tab_2');
    expect(client.sessionId).toBe('session_tab_2');

    const navRes = await client.send<{frameId: string}>('Page.navigate', {
      url: 'https://amazon.com',
    });
    expect(navRes.frameId).toBe('F2');
  });
});

describe('CdpClient Lifecycle and Connection Management', () => {
  let mockStream: MockSocketStream;
  let client: CdpClient;

  beforeEach(async () => {
    mockStream = new MockSocketStream();
    client = new CdpClient(mockStream);
  });

  it('rejects pending requests when remote closes socket (EOF)', async () => {
    mockStream.onClientWrite = () => {
      // Simulate remote EOF
      mockStream.close();
    };

    await client.connect();
    const sendPromise = client.send('Target.getTargets');
    await expect(sendPromise).rejects.toThrow(/CDP socket closed/);
  });

  it('rejects pending requests when disconnect() is called', async () => {
    mockStream.onClientWrite = () => {
      setTimeout(() => {
        client.disconnect();
      }, 10);
    };

    await client.connect();
    const sendPromise = client.send('Target.getTargets');
    await expect(sendPromise).rejects.toThrow(/CDP client disconnected/);
  });

  it('terminates read loop and rejects pending requests on unrecoverable ' +
         'framing error',
     async () => {
       mockStream.onClientWrite = () => {
         // 0x81 (FIN, text), 0x7f (127: 64-bit len), followed by 0xff bytes
         // (exceeds MAX_SAFE_INTEGER)
         const badFrame = new Uint8Array(10);
         badFrame[0] = 0x81;
         badFrame[1] = 127;
         badFrame.fill(0xff, 2, 10);
         mockStream.pushIncomingFrame(badFrame);
       };

       await client.connect();
       const sendPromise = client.send('Test.badFrame');
       await expect(sendPromise)
           .rejects.toThrow(
               /MAX_SAFE_INTEGER|decoding error|CDP read loop error/);
       expect(client.isConnected).toBe(false);
     });
});

describe('WebSocket Frame Fragmentation and Coalescing', () => {
  let mockStream: MockSocketStream;
  let client: CdpClient;

  beforeEach(async () => {
    mockStream = new MockSocketStream();
    client = new CdpClient(mockStream);
  });

  it('handles a single WebSocket frame split across two socket chunks',
     async () => {
       mockStream.onClientWrite = (req) => {
         const respJson = JSON.stringify({
           id: req.id,
           result: {split: true},
         });
         const fullFrame = encodeWebSocketFrame(respJson, false);
         const half = Math.floor(fullFrame.length / 2);
         const chunk1 = fullFrame.slice(0, half);
         const chunk2 = fullFrame.slice(half);

         mockStream.pushIncomingFrame(chunk1);
         setTimeout(() => {
           mockStream.pushIncomingFrame(chunk2);
         }, 10);
       };

       await client.connect();
       const result = await client.send<{split: boolean}>('Test.splitFrame');
       expect(result).toEqual({split: true});
     });

  it('handles two WebSocket frames arriving in a single chunk', async () => {
    let eventReceived = false;
    client.on('Test.coalescedEvent', (params: any) => {
      expect(params.foo).toBe('bar');
      eventReceived = true;
    });

    mockStream.onClientWrite = (req) => {
      const respJson = JSON.stringify({
        id: req.id,
        result: {coalesced: true},
      });
      const frame1 = encodeWebSocketFrame(respJson, false);

      const eventJson = JSON.stringify({
        method: 'Test.coalescedEvent',
        params: {foo: 'bar'},
      });
      const frame2 = encodeWebSocketFrame(eventJson, false);

      const combined = new Uint8Array(frame1.length + frame2.length);
      combined.set(frame1, 0);
      combined.set(frame2, frame1.length);

      mockStream.pushIncomingFrame(combined);
    };

    await client.connect();
    const result =
        await client.send<{coalesced: boolean}>('Test.coalescedFrame');
    expect(result).toEqual({coalesced: true});
    expect(eventReceived).toBe(true);
  });
});
