// Copyright 2026 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

import {getEffectiveGisToken} from './gis_auth';

export const TARGET_GCS_ARCHIVE_URL =
    'gs://chrome-partner-loadline/archive_phone_20260331.wprgo';

export const GCS_TOKEN_STORAGE_KEY = 'crossbench_gcs_access_token';

const DB_NAME = 'crossbench_gcs_cache';
const DB_VERSION = 1;
const STORE_NAME = 'archives';

export interface CachedGcsArchive {
  url: string;
  filename: string;
  md5Hash: string;
  size: number;
  data: Uint8Array;
  downloadedAt: number;
}

export interface GcsMetadata {
  name: string;
  bucket: string;
  size: number;
  md5Hash: string;
  updated?: string;
  etag?: string;
}

export function parseGcsUrl(
    url: string,
    ): {bucket: string; objectName: string} {
  if (!url.startsWith('gs://')) {
    throw new Error(`Invalid GCS URL (must start with gs://): ${url}`);
  }
  const withoutPrefix = url.substring(5);
  const slashIndex = withoutPrefix.indexOf('/');
  if (slashIndex === -1) {
    throw new Error(`Invalid GCS URL (missing object path): ${url}`);
  }
  const bucket = withoutPrefix.substring(0, slashIndex);
  const objectName = withoutPrefix.substring(slashIndex + 1);
  return {bucket, objectName};
}

export function safeFilename(name: string): string {
  return name.replace(/[^a-zA-Z0-9+\-_.]/g, '_').substring(0, 255);
}

export function getExpectedArchiveFilename(
    url: string,
    md5Hash: string,
    ): string {
  const {objectName} = parseGcsUrl(url);
  const lastSlash = objectName.lastIndexOf('/');
  const baseName =
      lastSlash !== -1 ? objectName.substring(lastSlash + 1) : objectName;
  const lastDot = baseName.lastIndexOf('.');
  const stem = lastDot !== -1 ? baseName.substring(0, lastDot) : baseName;
  const ext = lastDot !== -1 ? baseName.substring(lastDot) : '';
  const safeMd5 = safeFilename(md5Hash);
  return `${stem}_${safeMd5}${ext}`;
}

export function getManualAccessToken(): string {
  try {
    return localStorage.getItem(GCS_TOKEN_STORAGE_KEY) || '';
  } catch (err) {
    console.warn('Failed to read manual access token from localStorage:', err);
    return '';
  }
}

export function getStoredAccessToken(): string {
  const gisToken = getEffectiveGisToken();
  if (gisToken) {
    return gisToken;
  }
  return getManualAccessToken();
}

export function setStoredAccessToken(token: string): void {
  try {
    if (token.trim()) {
      localStorage.setItem(GCS_TOKEN_STORAGE_KEY, token.trim());
    } else {
      localStorage.removeItem(GCS_TOKEN_STORAGE_KEY);
    }
  } catch (err) {
    console.warn('Failed to save GCS access token to localStorage:', err);
  }
}

export function clearStoredAccessToken(): void {
  try {
    localStorage.removeItem(GCS_TOKEN_STORAGE_KEY);
  } catch (err) {
    console.warn('Failed to clear GCS access token from localStorage:', err);
  }
}

export function openGcsCacheDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === 'undefined') {
      return reject(
          new Error('IndexedDB is not available in this environment.'),
      );
    }
    try {
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      if (!request) {
        return reject(new Error('IndexedDB open returned null'));
      }
      const timeout = setTimeout(() => {
        reject(new Error('IndexedDB open timed out'));
      }, 3000);
      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME, {keyPath: 'url'});
        }
      };
      request.onsuccess = () => {
        clearTimeout(timeout);
        resolve(request.result);
      };
      request.onerror = () => {
        clearTimeout(timeout);
        reject(request.error);
      };
    } catch (err) {
      reject(err);
    }
  });
}

export async function getCachedGcsArchive(
    url: string,
    ): Promise<CachedGcsArchive|null> {
  try {
    const db = await openGcsCacheDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly');
      const store = tx.objectStore(STORE_NAME);
      const req = store.get(url);
      req.onsuccess = () => {
        const res = req.result;
        if (res && res.data) {
          if (!(res.data instanceof Uint8Array)) {
            res.data = new Uint8Array(res.data);
          }
          resolve(res as CachedGcsArchive);
        } else {
          resolve(null);
        }
      };
      req.onerror = () => reject(req.error);
    });
  } catch (err) {
    console.warn('Failed to read from GCS IndexedDB cache:', err);
    return null;
  }
}

export async function setCachedGcsArchive(
    archive: CachedGcsArchive,
    ): Promise<void> {
  const db = await openGcsCacheDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const req = store.put(archive);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

export async function deleteCachedGcsArchive(url: string): Promise<void> {
  const db = await openGcsCacheDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const req = store.delete(url);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

async function fetchGcsEndpoint(
    url: string,
    token: string,
    extraInit?: RequestInit,
    ): Promise<Response> {
  const headers = new Headers(extraInit?.headers);
  if (token && token.trim()) {
    headers.set('Authorization', `Bearer ${token.trim()}`);
  }
  const init: RequestInit = {
    ...extraInit,
    headers,
  };

  try {
    return await fetch(url, init);
  } catch (err) {
    const isLocalhost = typeof window !== 'undefined' &&
        window.location?.hostname === 'localhost';
    const isNetworkOrCorsError = err instanceof TypeError;

    if (isLocalhost && isNetworkOrCorsError &&
        url.startsWith('https://storage.googleapis.com/')) {
      console.warn(
          `Direct fetch to ${url} failed (likely CORS). ` +
              'Attempting /gcs-proxy...',
          err,
      );
      const proxyUrl = url.replace(
          'https://storage.googleapis.com/',
          '/gcs-proxy/',
      );
      return await fetch(proxyUrl, init);
    }
    throw err;
  }
}

export async function fetchGcsMetadata(
    url: string,
    token: string,
    ): Promise<GcsMetadata> {
  const {bucket, objectName} = parseGcsUrl(url);
  const encodedObject = encodeURIComponent(objectName);
  const metaUrl = `https://storage.googleapis.com/storage/v1/b/${bucket}/o/${
      encodedObject}`;

  const res = await fetchGcsEndpoint(metaUrl, token);
  if (!res.ok) {
    const errText = await res.text().catch(() => '');
    if (res.status === 401 || res.status === 403) {
      throw new Error(
          `Authentication failed (${res.status} ${res.statusText}). ` +
              `Please check your GCP access token. Details: ${errText}`,
      );
    }
    throw new Error(
        `Failed to fetch GCS metadata for ${url} ` +
            `(${res.status} ${res.statusText}): ${errText}`,
    );
  }
  const json = await res.json();
  return {
    name: json.name || objectName,
    bucket: json.bucket || bucket,
    size: parseInt(json.size || '0', 10),
    md5Hash: json.md5Hash || '',
    updated: json.updated,
    etag: json.etag,
  };
}

export async function downloadGcsArchive(
    url: string,
    token: string,
    onProgress?: (loaded: number, total: number) => void,
    ): Promise<CachedGcsArchive> {
  const {bucket, objectName} = parseGcsUrl(url);
  const encodedObject = encodeURIComponent(objectName);

  const metadata = await fetchGcsMetadata(url, token);
  if (!metadata.md5Hash || !metadata.md5Hash.trim()) {
    throw new Error(`GCS metadata for ${url} is missing md5Hash.`);
  }

  const mediaUrl = `https://storage.googleapis.com/storage/v1/b/${bucket}/o/` +
      `${encodedObject}?alt=media`;
  const res = await fetchGcsEndpoint(mediaUrl, token);
  if (!res.ok) {
    const errText = await res.text().catch(() => '');
    if (res.status === 401 || res.status === 403) {
      throw new Error(
          `GCS download authorization error (${res.status} ${
              res.statusText}). ` +
              `Please refresh your access token. Details: ${errText}`,
      );
    }
    throw new Error(
        `GCS download failed for ${url} ` +
            `(${res.status} ${res.statusText}): ${errText}`,
    );
  }

  const contentLengthHeader = res.headers.get('Content-Length');
  const totalBytes = contentLengthHeader ? parseInt(contentLengthHeader, 10) :
                                           metadata.size || 0;

  let completeData: Uint8Array;
  const reader = res.body?.getReader();
  if (reader) {
    let receivedBytes = 0;
    const chunks: Uint8Array[] = [];
    while (true) {
      const {done, value} = await reader.read();
      if (done)
        break;
      if (value) {
        chunks.push(value);
        receivedBytes += value.length;
        if (onProgress) {
          onProgress(receivedBytes, totalBytes);
        }
      }
    }
    completeData = new Uint8Array(receivedBytes);
    let offset = 0;
    for (const chunk of chunks) {
      completeData.set(chunk, offset);
      offset += chunk.length;
    }
  } else {
    const buffer = await res.arrayBuffer();
    completeData = new Uint8Array(buffer);
    if (onProgress) {
      onProgress(completeData.length, completeData.length);
    }
  }

  const filename = getExpectedArchiveFilename(url, metadata.md5Hash);
  const archive: CachedGcsArchive = {
    url,
    filename,
    md5Hash: metadata.md5Hash,
    size: completeData.length,
    data: completeData,
    downloadedAt: Date.now(),
  };

  await setCachedGcsArchive(archive);
  return archive;
}
