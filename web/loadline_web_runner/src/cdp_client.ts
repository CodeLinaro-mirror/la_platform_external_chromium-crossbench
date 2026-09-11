// Copyright 2026 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

/**
 * Chrome DevTools Protocol (CDP) Client.
 *
 * Communicates over WebADB stream / DevToolsSocketStream or WebSocket.
 * Supports CDP command execution (Page.navigate) and event listeners
 * (Page.loadEventFired).
 */

import {DevToolsSocketStream} from './devtools_discovery';

export interface CdpRequest {
  id: number;
  method: string;
  params?: Record<string, unknown>;
  sessionId?: string;
}

export type CdpEventHandler<T = any> = (params: T) => void;

/**
 * Encodes text or payload into a client-side WebSocket frame (FIN=1, Opcode=1,
 * Masked).
 */
export function encodeWebSocketFrame(
    payload: string|Uint8Array, masked: boolean = true): Uint8Array {
  const data =
      typeof payload === 'string' ? new TextEncoder().encode(payload) : payload;

  const length = data.length;
  let headerLength = 2;

  if (length > 65535) {
    headerLength += 8;
  } else if (length > 125) {
    headerLength += 2;
  }

  if (masked) {
    headerLength += 4;
  }

  const frame = new Uint8Array(headerLength + length);
  frame[0] = 0x81;  // FIN bit set, Opcode = 1 (Text frame)

  let offset = 2;
  if (length > 65535) {
    frame[1] = masked ? 0x80 | 127 : 127;
    const view = new DataView(frame.buffer, frame.byteOffset);
    view.setBigUint64(2, BigInt(length), false);
    offset = 10;
  } else if (length > 125) {
    frame[1] = masked ? 0x80 | 126 : 126;
    const view = new DataView(frame.buffer, frame.byteOffset);
    view.setUint16(2, length, false);
    offset = 4;
  } else {
    frame[1] = masked ? 0x80 | length : length;
  }

  if (masked) {
    const maskKey = new Uint8Array(4);
    crypto.getRandomValues(maskKey);
    frame.set(maskKey, offset);
    offset += 4;

    for (let i = 0; i < length; i++) {
      frame[offset + i] = data[i] ^ maskKey[i % 4];
    }
  } else {
    frame.set(data, offset);
  }

  return frame;
}

/**
 * Decodes a single WebSocket frame from a buffer.
 * Returns null if the buffer does not yet contain a complete frame.
 */
export function decodeWebSocketFrame(buffer: Uint8Array): {
  fin: boolean; opcode: number; payload: Uint8Array; bytesConsumed: number;
}|null {
  if (buffer.length < 2) {
    return null;
  }

  const fin = (buffer[0] & 0x80) !== 0;
  const opcode = buffer[0] & 0x0f;
  const isMasked = (buffer[1] & 0x80) !== 0;
  let payloadLen = buffer[1] & 0x7f;

  let offset = 2;
  if (payloadLen === 126) {
    if (buffer.length < 4) {
      return null;
    }
    payloadLen = (buffer[2] << 8) | buffer[3];
    offset = 4;
  } else if (payloadLen === 127) {
    if (buffer.length < 10) {
      return null;
    }
    const view =
        new DataView(buffer.buffer, buffer.byteOffset, buffer.byteLength);
    const bigLen = view.getBigUint64(2, false);
    if (bigLen > BigInt(Number.MAX_SAFE_INTEGER)) {
      throw new Error('WebSocket frame payload exceeds MAX_SAFE_INTEGER');
    }
    payloadLen = Number(bigLen);
    offset = 10;
  }

  let maskOffset = -1;
  if (isMasked) {
    if (buffer.length < offset + 4) {
      return null;
    }
    maskOffset = offset;
    offset += 4;
  }

  const totalLen = offset + payloadLen;
  if (buffer.length < totalLen) {
    return null;
  }

  const payload = new Uint8Array(payloadLen);
  if (isMasked) {
    for (let i = 0; i < payloadLen; i++) {
      payload[i] = buffer[offset + i] ^ buffer[maskOffset + (i % 4)];
    }
  } else {
    payload.set(buffer.subarray(offset, totalLen));
  }

  return {fin, opcode, payload, bytesConsumed: totalLen};
}

/**
 * Chrome DevTools Protocol Client over socket/websocket stream.
 */
export class CdpClient {
  private socket: DevToolsSocketStream|null = null;
  private nextId = 1;
  private pendingRequests = new Map < number, {
    resolve: (value: any) => void;
    reject: (reason?: any) => void
  }
  >();
  private eventHandlers = new Map<string, Set<CdpEventHandler>>();
  private readLoopRunning = false;
  private activeSessionId: string|null = null;

  constructor(socket?: DevToolsSocketStream) {
    if (socket) {
      this.socket = socket;
    }
  }

  get isConnected(): boolean {
    return this.socket !== null && this.readLoopRunning;
  }

  get sessionId(): string|null {
    return this.activeSessionId;
  }

  /**
   * Rejects all in-flight pending requests with an error and clears the
   * pending map.
   */
  private terminatePendingRequests(error: Error): void {
    for (const {reject} of this.pendingRequests.values()) {
      reject(error);
    }
    this.pendingRequests.clear();
  }

  /**
   * Discovers the initial page target on the browser endpoint and attaches
   * to it.
   */
  async initBrowserSession(): Promise<string> {
    const res =
        await this
            .send<{targetInfos?: Array<{targetId: string; type: string}>;}>(
                'Target.getTargets');
    let pageTarget = res?.targetInfos?.find((t) => t.type === 'page');
    let targetId = pageTarget?.targetId;
    if (!targetId) {
      const created = await this.send<{targetId: string}>(
          'Target.createTarget', {url: 'about:blank'});
      targetId = created?.targetId;
    }
    if (!targetId) {
      throw new Error('Failed to find or create page target');
    }
    const attachRes =
        await this.send<{sessionId: string}>('Target.attachToTarget', {
          targetId,
          flatten: true,
        });
    const sessionId = attachRes?.sessionId;
    if (!sessionId) {
      throw new Error(
          `Target.attachToTarget failed to return a sessionId for target ` +
          `${targetId}`);
    }
    this.activeSessionId = sessionId;
    return sessionId;
  }

  /**
   * Creates a new page target and attaches to it as the active session.
   */
  async switchTab(url: string = 'about:blank'): Promise<string> {
    const createRes =
        await this.send<{targetId: string}>('Target.createTarget', {url});
    const targetId = createRes?.targetId;
    if (!targetId) {
      throw new Error(
          `Target.createTarget failed: ${JSON.stringify(createRes)}`);
    }
    const attachRes =
        await this.send<{sessionId: string}>('Target.attachToTarget', {
          targetId,
          flatten: true,
        });
    const sessionId = attachRes?.sessionId;
    if (!sessionId) {
      throw new Error(`Target.attachToTarget failed for target ${targetId}: ${
          JSON.stringify(attachRes)}`);
    }
    this.activeSessionId = sessionId;
    try {
      await this.send('Target.activateTarget', {targetId});
    } catch (err) {
      console.debug('Target.activateTarget failed (non-fatal):', err);
    }
    return sessionId;
  }

  /**
   * Connects or attaches the socket stream to the CDP Client.
   */
  async connect(socket?: DevToolsSocketStream, upgradePath?: string):
      Promise<void> {
    if (socket) {
      this.socket = socket;
    }
    if (!this.socket) {
      throw new Error('No DevToolsSocketStream provided to CdpClient');
    }

    let initialBuffer: Uint8Array = new Uint8Array(0);
    // Perform HTTP Upgrade handshake if upgradePath is provided
    if (upgradePath) {
      initialBuffer = await this.performHttpUpgrade(upgradePath);
    }

    // Start background reader loop if not already running
    if (!this.readLoopRunning) {
      this.readLoopRunning = true;
      this.startReadLoop(initialBuffer).catch((err) => {
        console.error('CDP read loop error:', err);
      });
    }
  }

  /**
   * Sends an HTTP 1.1 WebSocket Upgrade request to the CDP endpoint and waits
   * for HTTP 101 Switching Protocols.
   */
  private async performHttpUpgrade(upgradePath: string): Promise<Uint8Array> {
    if (!this.socket) {
      throw new Error('CDP client is not connected to a socket');
    }
    const key = 'dGhlIHNhbXBsZSBub25jZQ==';
    const reqText = `GET ${upgradePath} HTTP/1.1\r\n` +
        'Host: localhost\r\n' +
        'Upgrade: websocket\r\n' +
        'Connection: Upgrade\r\n' +
        `Sec-WebSocket-Key: ${key}\r\n` +
        'Sec-WebSocket-Version: 13\r\n\r\n';

    await this.socket.write(new TextEncoder().encode(reqText));

    let headerBuffer = new Uint8Array(0);
    while (true) {
      const chunk = await this.socket.read();
      if (!chunk) {
        throw new Error(
            'Socket closed while waiting for ' +
            'HTTP 101 WebSocket Upgrade response');
      }
      const newBuffer = new Uint8Array(headerBuffer.length + chunk.length);
      newBuffer.set(headerBuffer, 0);
      newBuffer.set(chunk, headerBuffer.length);
      headerBuffer = newBuffer;

      const text = new TextDecoder().decode(headerBuffer);
      const headerEndIndex = text.indexOf('\r\n\r\n');
      if (headerEndIndex !== -1) {
        const headers = text.slice(0, headerEndIndex);
        if (!headers.includes('101 ')) {
          throw new Error(
              `HTTP WebSocket Upgrade failed. Server responded with:\n${
                  headers}`);
        }
        return headerBuffer.slice(headerEndIndex + 4);
      }
    }
  }

  /**
   * Sends a raw CDP method call and waits for response.
   */
  async send<T = unknown>(
      method: string, params?: Record<string, unknown>,
      sessionId?: string): Promise<T> {
    if (!this.socket || !this.readLoopRunning) {
      throw new Error('CDP client is not connected to a socket');
    }

    const id = this.nextId++;
    const sid = sessionId !== undefined ? sessionId :
        !method.startsWith('Target.') && !method.startsWith('Browser.') ?
                                          this.activeSessionId ?? undefined :
                                          undefined;

    const request: CdpRequest = {
      id,
      method,
      params,
      ...(sid ? {sessionId: sid} : {}),
    };
    const payloadJson = JSON.stringify(request);
    const frame = encodeWebSocketFrame(payloadJson, true);

    const promise = new Promise<T>((resolve, reject) => {
      this.pendingRequests.set(id, {resolve, reject});
    });

    try {
      await this.socket.write(frame);
    } catch (err) {
      this.pendingRequests.delete(id);
      throw err;
    }

    const result = await promise;

    if (method === 'Target.attachToTarget' && (result as any)?.sessionId) {
      this.activeSessionId = (result as any).sessionId;
    }

    return result;
  }

  /**
   * Subscribes to a CDP event by method name (e.g., 'Page.loadEventFired').
   */
  on<T = any>(eventName: string, handler: CdpEventHandler<T>): void {
    if (!this.eventHandlers.has(eventName)) {
      this.eventHandlers.set(eventName, new Set());
    }
    this.eventHandlers.get(eventName)!.add(handler);
  }

  /**
   * Unsubscribes from a CDP event.
   */
  off<T = any>(eventName: string, handler: CdpEventHandler<T>): void {
    const handlers = this.eventHandlers.get(eventName);
    if (handlers) {
      handlers.delete(handler);
    }
  }

  /**
   * Dispatches incoming JSON message to pending requests or event handlers.
   */
  handleIncomingMessage(messageJson: string): void {
    try {
      const msg = JSON.parse(messageJson);

      // Check if it's a command response
      if (typeof msg.id === 'number' && this.pendingRequests.has(msg.id)) {
        const {resolve, reject} = this.pendingRequests.get(msg.id)!;
        this.pendingRequests.delete(msg.id);
        if (msg.error) {
          const data = msg.error.data ? typeof msg.error.data === 'string' ?
                                        msg.error.data :
                                        JSON.stringify(msg.error.data) :
                                        '';
          reject(new Error(`CDP Error ${msg.error.code}: ${msg.error.message}${
              data ? ' (' + data + ')' : ''}`));
        } else {
          resolve(msg.result);
        }
        return;
      }

      // Check if it's an event
      if (msg.method) {
        this.dispatchDomainEvent(msg.method, msg.params);
      }
    } catch (err) {
      console.warn(
          'Failed to parse incoming CDP message JSON:', messageJson, err);
    }
  }

  /**
   * Dispatches domain events to registered listeners.
   */
  private dispatchDomainEvent(method: string, params: any): void {
    const handlers = this.eventHandlers.get(method);
    if (handlers) {
      for (const handler of handlers) {
        try {
          handler(params);
        } catch (err) {
          console.error(`Error in event handler for ${method}:`, err);
        }
      }
    }
  }

  /**
   * Triggers Page.navigate and waits for optional Page.loadEventFired.
   */
  async navigate(url: string, waitForLoadEvent: boolean = true):
      Promise<{frameId: string; loaderId?: string}> {
    await this.send('Page.enable');

    let handler: (() => void)|undefined;
    let loadPromise: Promise<void>|null = null;
    if (waitForLoadEvent) {
      loadPromise = new Promise<void>((resolve) => {
        handler = () => resolve();
        this.on('Page.loadEventFired', handler);
      });
    }

    try {
      const navResult = await this.send<{frameId: string; loaderId?: string}>(
          'Page.navigate', {url});

      if (loadPromise) {
        await loadPromise;
      }

      return navResult;
    } finally {
      if (handler) {
        this.off('Page.loadEventFired', handler);
      }
    }
  }

  /**
   * Background loop reading incoming raw WebSocket frames from socket.
   */
  private async startReadLoop(initialBuffer: Uint8Array = new Uint8Array(0)):
      Promise<void> {
    let buffer = initialBuffer;

    try {
      while (this.readLoopRunning && this.socket) {
        let frame: ReturnType<typeof decodeWebSocketFrame>;
        while ((frame = decodeWebSocketFrame(buffer))) {
          buffer = buffer.subarray(frame.bytesConsumed);
          if (frame.opcode === 1) {
            const text = new TextDecoder().decode(frame.payload);
            this.handleIncomingMessage(text);
          } else if (frame.opcode === 8) {
            this.readLoopRunning = false;
            this.terminatePendingRequests(new Error(
                'WebSocket connection closed by remote (close frame)'));
            return;
          }
        }

        const chunk = await this.socket.read();
        if (chunk === null) {
          // Socket closed / EOF
          this.readLoopRunning = false;
          this.terminatePendingRequests(
              new Error('CDP socket closed (EOF received)'));
          return;
        }

        if (buffer.length === 0) {
          buffer = chunk;
        } else {
          const combined = new Uint8Array(buffer.length + chunk.length);
          combined.set(buffer, 0);
          combined.set(chunk, buffer.length);
          buffer = combined;
        }
      }
    } catch (err: any) {
      this.readLoopRunning = false;
      this.terminatePendingRequests(
          new Error(`CDP read loop error: ${err?.message ?? String(err)}`));
      throw err;
    } finally {
      this.readLoopRunning = false;
    }
  }

  /**
   * Closes the client connection and rejects all in-flight pending requests.
   */
  async disconnect(): Promise<void> {
    this.readLoopRunning = false;
    this.terminatePendingRequests(new Error('CDP client disconnected'));
    if (this.socket) {
      const sock = this.socket;
      this.socket = null;
      await sock.close();
    }
  }
}
