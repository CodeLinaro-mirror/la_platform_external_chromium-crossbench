// Copyright 2026 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

/**
 * WebADB RSA Keypair Generation and IndexedDB Credential Store.
 */

import {type AdbCredentialStore, type AdbPrivateKey} from '@yume-chan/adb';

export const ADB_CREDENTIALS_DB_NAME = 'adb_credentials';
export const ADB_CREDENTIALS_DB_VERSION = 1;
export const ADB_CREDENTIALS_STORE_NAME = 'keys';

export function openAdbCredentialDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === 'undefined') {
      return reject(
          new Error('IndexedDB is not available in this environment.'));
    }
    const request =
        indexedDB.open(ADB_CREDENTIALS_DB_NAME, ADB_CREDENTIALS_DB_VERSION);
    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains(ADB_CREDENTIALS_STORE_NAME)) {
        db.createObjectStore(ADB_CREDENTIALS_STORE_NAME, {
          autoIncrement: true,
        });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function getStoredAdbKeys(): Promise<AdbPrivateKey[]> {
  if (typeof indexedDB === 'undefined') {
    return [];
  }
  const db = await openAdbCredentialDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(ADB_CREDENTIALS_STORE_NAME, 'readonly');
    const store = tx.objectStore(ADB_CREDENTIALS_STORE_NAME);
    const req = store.getAll();
    let keys: AdbPrivateKey[] = [];

    req.onsuccess = () => {
      const results = req.result || [];
      keys = results.map((item: any) => ({
                           buffer: item.buffer instanceof Uint8Array ?
                               item.buffer :
                               new Uint8Array(item.buffer),
                           name: item.name,
                         }));
    };
    tx.oncomplete = () => {
      db.close();
      resolve(keys);
    };
    tx.onerror = () => {
      db.close();
      reject(tx.error);
    };
  });
}

export async function saveStoredAdbKey(key: AdbPrivateKey): Promise<void> {
  if (typeof indexedDB === 'undefined') {
    return;
  }
  const db = await openAdbCredentialDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(ADB_CREDENTIALS_STORE_NAME, 'readwrite');
    const store = tx.objectStore(ADB_CREDENTIALS_STORE_NAME);
    store.add({
      buffer: key.buffer,
      name: key.name,
    });
    tx.oncomplete = () => {
      db.close();
      resolve();
    };
    tx.onerror = () => {
      db.close();
      reject(tx.error);
    };
  });
}

/**
 * Persistent RSA Credential Store for WebADB authentication.
 * Uses Web Crypto API to generate RSA-2048 keys and IndexedDB for persistence.
 */
export class WebAdbCredentialStore implements AdbCredentialStore {
  private inMemoryKeys: AdbPrivateKey[] = [];

  private get hasIndexedDb(): boolean {
    return typeof indexedDB !== 'undefined';
  }

  async generateKey(): Promise<AdbPrivateKey> {
    if (!globalThis.crypto?.subtle) {
      throw new Error('Web Crypto API (crypto.subtle) is not available');
    }

    const keyPair = await globalThis.crypto.subtle.generateKey(
        {
          name: 'RSASSA-PKCS1-v1_5',
          modulusLength: 2048,
          publicExponent: new Uint8Array([0x01, 0x00, 0x01]),
          hash: 'SHA-1',
        },
        true, ['sign']);

    const pkcs8 =
        await globalThis.crypto.subtle.exportKey('pkcs8', keyPair.privateKey);
    const key: AdbPrivateKey = {
      buffer: new Uint8Array(pkcs8),
      name: 'crossbench@web',
    };

    if (this.hasIndexedDb) {
      await saveStoredAdbKey(key);
    } else {
      this.inMemoryKeys.push(key);
    }
    return key;
  }

  async * iterateKeys(): AsyncIterable<AdbPrivateKey> {
    if (this.hasIndexedDb) {
      const storedKeys = await getStoredAdbKeys();
      for (const key of storedKeys) {
        yield key;
      }
    } else {
      for (const key of this.inMemoryKeys) {
        yield key;
      }
    }
  }
}
