// Copyright 2026 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

/**
 * Chrome DevTools Socket Stream and Target Discovery Utilities.
 */

/**
 * Interface representing a bidirectional devtools socket stream.
 */
export interface DevToolsSocketStream {
  write(data: Uint8Array): Promise<void>;
  read(): Promise<Uint8Array|null>;
  close(): Promise<void>;
}

/**
 * Mockable DevTools socket wrapper around WebADB socket.
 */
export class WebAdbSocketStream implements DevToolsSocketStream {
  private reader: ReadableStreamDefaultReader<Uint8Array>;
  private writer: WritableStreamDefaultWriter<Uint8Array>;
  private closeCallback?: () => Promise<void>;

  constructor(
      readable: ReadableStream<Uint8Array>,
      writable: WritableStream<Uint8Array>,
      closeCallback?: () => Promise<void>) {
    this.reader = readable.getReader();
    this.writer = writable.getWriter();
    this.closeCallback = closeCallback;
  }

  async write(data: Uint8Array): Promise<void> {
    await this.writer.write(data);
  }

  async read(): Promise<Uint8Array|null> {
    const result = await this.reader.read();
    if (result.done) {
      return null;
    }
    return result.value;
  }

  async close(): Promise<void> {
    try {
      await this.writer.close();
    } catch {
      // Writer may already be closed or errored.
    } finally {
      this.writer.releaseLock();
    }

    try {
      await this.reader.cancel();
    } catch {
      // Reader may already be closed or errored.
    } finally {
      this.reader.releaseLock();
    }

    if (this.closeCallback) {
      await this.closeCallback();
    }
  }
}

/**
 * Returns the relative CDP WebSocket upgrade path for the browser endpoint.
 *
 * "Upgrade" refers to the HTTP-to-WebSocket protocol switch (RFC 6455)
 * performed over the raw DevTools socket (e.g. `GET /devtools/browser/...`
 * with `Upgrade: websocket` to transition the stream to WebSocket frames).
 */
export function getBrowserUpgradePath(
    versionInfo?: {webSocketDebuggerUrl?: string;}): string {
  if (!versionInfo?.webSocketDebuggerUrl) {
    throw new Error(
        'Missing webSocketDebuggerUrl in DevTools version response.');
  }
  const idx = versionInfo.webSocketDebuggerUrl.indexOf('/devtools/browser');
  if (idx === -1) {
    throw new Error(
        `Invalid webSocketDebuggerUrl: "${versionInfo.webSocketDebuggerUrl}" ` +
        'does not contain "/devtools/browser".');
  }
  return versionInfo.webSocketDebuggerUrl.slice(idx);
}
