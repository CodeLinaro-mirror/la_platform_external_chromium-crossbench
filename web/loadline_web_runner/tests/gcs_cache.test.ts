// Copyright 2026 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

import {beforeEach, describe, expect, it, vi} from 'vitest';

import {type CachedGcsArchive, clearStoredAccessToken, deleteCachedGcsArchive, downloadGcsArchive, fetchGcsMetadata, getCachedGcsArchive, getExpectedArchiveFilename, getStoredAccessToken, parseGcsUrl, safeFilename, setCachedGcsArchive, setStoredAccessToken, TARGET_GCS_ARCHIVE_URL,} from '../src/gcs_cache';

describe('GCS Cache & Utility Functions', () => {
  let idbStorage: Map<string, any>;

  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
    idbStorage = new Map<string, any>();
    const mockStore = {
      get: (key: string) => {
        const req: any = {result: idbStorage.get(key)};
        setTimeout(() => req.onsuccess && req.onsuccess(), 0);
        return req;
      },
      put: (val: any) => {
        idbStorage.set(val.url, val);
        const req: any = {};
        setTimeout(() => req.onsuccess && req.onsuccess(), 0);
        return req;
      },
      delete: (key: string) => {
        idbStorage.delete(key);
        const req: any = {};
        setTimeout(() => req.onsuccess && req.onsuccess(), 0);
        return req;
      },
    };
    const mockDb: any = {
      transaction: () => ({
        objectStore: () => mockStore,
      }),
    };
    const mockOpenReq: any = {
      result: mockDb,
    };
    (global as any).indexedDB = {
      open: () => {
        setTimeout(() => {
          if (mockOpenReq.onsuccess)
            mockOpenReq.onsuccess();
        }, 0);
        return mockOpenReq;
      },
    };
  });

  describe('parseGcsUrl', () => {
    it('parses bucket and object name correctly', () => {
      const parsed = parseGcsUrl(
          'gs://chrome-partner-loadline/archive_phone_20260331.wprgo',
      );
      expect(parsed.bucket).toBe('chrome-partner-loadline');
      expect(parsed.objectName).toBe('archive_phone_20260331.wprgo');
    });

    it('parses nested object paths correctly', () => {
      const parsed = parseGcsUrl('gs://my-bucket/nested/dir/file.wprgo');
      expect(parsed.bucket).toBe('my-bucket');
      expect(parsed.objectName).toBe('nested/dir/file.wprgo');
    });

    it('throws on non-gs scheme', () => {
      expect(() => parseGcsUrl('https://storage.googleapis.com/b/o'))
          .toThrow(
              /Invalid GCS URL/,
          );
    });

    it('throws on missing object name', () => {
      expect(() => parseGcsUrl('gs://only-bucket'))
          .toThrow(
              /missing object path/,
          );
    });
  });

  describe('safeFilename', () => {
    it('preserves alphanumeric and safe characters', () => {
      expect(safeFilename('archive_phone-2026+test.wprgo'))
          .toBe(
              'archive_phone-2026+test.wprgo',
          );
    });

    it('replaces unsafe characters like slash and equal sign', () => {
      expect(safeFilename('abc/123=xyz')).toBe('abc_123_xyz');
    });
  });

  describe('getExpectedArchiveFilename', () => {
    it('generates filename matching crossbench safe_md5 pattern', () => {
      const filename = getExpectedArchiveFilename(
          'gs://chrome-partner-loadline/archive_phone_20260331.wprgo',
          'AbCdEf123==',
      );
      expect(filename).toBe('archive_phone_20260331_AbCdEf123__.wprgo');
    });
  });

  describe('Access Token Storage', () => {
    it('gets, sets, and clears tokens in localStorage', () => {
      expect(getStoredAccessToken()).toBe('');
      setStoredAccessToken('mock_test_token_123');
      expect(getStoredAccessToken()).toBe('mock_test_token_123');
      clearStoredAccessToken();
      expect(getStoredAccessToken()).toBe('');
    });
  });

  describe('IndexedDB GCS Cache', () => {
    it('stores, retrieves, and deletes cached archives with mock indexedDB',
       async () => {
         const testArchive: CachedGcsArchive = {
           url: TARGET_GCS_ARCHIVE_URL,
           filename: 'archive_phone_20260331_mockhash.wprgo',
           md5Hash: 'mockhash',
           size: 10,
           data: new Uint8Array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]),
           downloadedAt: 1234567890,
         };

         await setCachedGcsArchive(testArchive);
         const retrieved = await getCachedGcsArchive(TARGET_GCS_ARCHIVE_URL);
         expect(retrieved).not.toBeNull();
         expect(retrieved?.filename)
             .toBe('archive_phone_20260331_mockhash.wprgo');
         expect(retrieved?.data.length).toBe(10);

         await deleteCachedGcsArchive(TARGET_GCS_ARCHIVE_URL);
         const afterDelete = await getCachedGcsArchive(TARGET_GCS_ARCHIVE_URL);
         expect(afterDelete).toBeNull();
       });

    it('rejects when setCachedGcsArchive encounters an IndexedDB error',
       async () => {
         const mockStore = {
           put: () => {
             const req: any = {error: new Error('QuotaExceededError')};
             setTimeout(() => req.onerror && req.onerror(), 0);
             return req;
           },
         };
         const mockDb: any = {
           transaction: () => ({
             objectStore: () => mockStore,
           }),
         };
         const mockOpenReq: any = {result: mockDb};
         (global as any).indexedDB = {
           open: () => {
             setTimeout(
                 () => mockOpenReq.onsuccess && mockOpenReq.onsuccess(), 0);
             return mockOpenReq;
           },
         };

         const testArchive: CachedGcsArchive = {
           url: TARGET_GCS_ARCHIVE_URL,
           filename: 'archive.wprgo',
           md5Hash: 'hash',
           size: 4,
           data: new Uint8Array([1, 2, 3, 4]),
           downloadedAt: 12345,
         };

         await expect(setCachedGcsArchive(testArchive))
             .rejects.toThrow(
                 'QuotaExceededError',
             );
       });

    it('rejects when deleteCachedGcsArchive encounters an IndexedDB error',
       async () => {
         const mockStore = {
           delete: () => {
             const req: any = {error: new Error('DeleteFailedError')};
             setTimeout(() => req.onerror && req.onerror(), 0);
             return req;
           },
         };
         const mockDb: any = {
           transaction: () => ({
             objectStore: () => mockStore,
           }),
         };
         const mockOpenReq: any = {result: mockDb};
         (global as any).indexedDB = {
           open: () => {
             setTimeout(
                 () => mockOpenReq.onsuccess && mockOpenReq.onsuccess(), 0);
             return mockOpenReq;
           },
         };

         await expect(
             deleteCachedGcsArchive(TARGET_GCS_ARCHIVE_URL),
             )
             .rejects.toThrow('DeleteFailedError');
       });
  });

  describe('fetchGcsMetadata', () => {
    it('fetches metadata with Authorization Bearer header', async () => {
      const mockMeta = {
        name: 'archive_phone_20260331.wprgo',
        bucket: 'chrome-partner-loadline',
        size: '12345678',
        md5Hash: 'testHash123==',
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => mockMeta,
      });

      const meta = await fetchGcsMetadata(TARGET_GCS_ARCHIVE_URL, 'test_token');
      expect(meta.size).toBe(12345678);
      expect(meta.md5Hash).toBe('testHash123==');
      expect(global.fetch)
          .toHaveBeenCalledWith(
              expect.stringContaining('chrome-partner-loadline'),
              expect.objectContaining({
                headers: expect.any(Headers),
              }),
          );
    });

    it('throws informative error on 401/403 authorization failures',
       async () => {
         global.fetch = vi.fn().mockResolvedValue({
           ok: false,
           status: 401,
           statusText: 'Unauthorized',
           text: async () => 'Invalid Credentials',
         });

         await expect(
             fetchGcsMetadata(TARGET_GCS_ARCHIVE_URL, 'bad_token'),
             )
             .rejects.toThrow(
                 /Authentication failed \(401 Unauthorized\)/,
             );
       });

    it('attempts /gcs-proxy fallback on TypeError CORS failure on localhost',
       async () => {
         const mockMeta = {
           name: 'archive_phone_20260331.wprgo',
           bucket: 'chrome-partner-loadline',
           size: '12345',
           md5Hash: 'proxyHash',
         };

         global.fetch =
             vi.fn()
                 .mockRejectedValueOnce(new TypeError('Failed to fetch (CORS)'))
                 .mockResolvedValueOnce({
                   ok: true,
                   status: 200,
                   json: async () => mockMeta,
                 });

         const meta =
             await fetchGcsMetadata(TARGET_GCS_ARCHIVE_URL, 'test_token');
         expect(meta.md5Hash).toBe('proxyHash');
         expect(global.fetch).toHaveBeenCalledTimes(2);
         expect(global.fetch)
             .toHaveBeenLastCalledWith(
                 expect.stringContaining('/gcs-proxy/'),
                 expect.any(Object),
             );
       });

    it('does not fall back to /gcs-proxy on HTTP 500 server error',
       async () => {
         global.fetch = vi.fn().mockResolvedValue({
           ok: false,
           status: 500,
           statusText: 'Internal Server Error',
           text: async () => 'Backend crash',
         });

         await expect(
             fetchGcsMetadata(TARGET_GCS_ARCHIVE_URL, 'test_token'),
             )
             .rejects.toThrow(/500 Internal Server Error/);
         expect(global.fetch).toHaveBeenCalledTimes(1);
       });
  });

  describe('downloadGcsArchive', () => {
    it('downloads media and computes expected archive with arrayBuffer',
       async () => {
         const testBytes = new Uint8Array([1, 2, 3, 4, 5, 6, 7, 8]);
         const mockMeta = {
           name: 'archive_phone_20260331.wprgo',
           bucket: 'chrome-partner-loadline',
           size: '8',
           md5Hash: 'hash8bytes',
         };

         global.fetch = vi.fn()
                            .mockResolvedValueOnce({
                              ok: true,
                              status: 200,
                              json: async () => mockMeta,
                            })
                            .mockResolvedValueOnce({
                              ok: true,
                              status: 200,
                              headers: new Headers({'Content-Length': '8'}),
                              arrayBuffer: async () => testBytes.buffer,
                            });

         let progressCalls = 0;
         const archive = await downloadGcsArchive(
             TARGET_GCS_ARCHIVE_URL,
             'test_token',
             () => {
               progressCalls++;
             },
         );

         expect(archive.url).toBe(TARGET_GCS_ARCHIVE_URL);
         expect(archive.filename)
             .toBe('archive_phone_20260331_hash8bytes.wprgo');
         expect(archive.size).toBe(8);
         expect(archive.data.length).toBe(8);
         expect(progressCalls).toBeGreaterThan(0);
       });

    it('downloads media using streaming reader (res.body.getReader())',
       async () => {
         const chunk1 = new Uint8Array([1, 2, 3, 4]);
         const chunk2 = new Uint8Array([5, 6, 7, 8]);
         const mockMeta = {
           name: 'archive_phone_20260331.wprgo',
           bucket: 'chrome-partner-loadline',
           size: '8',
           md5Hash: 'streaming_md5',
         };

         let readStep = 0;
         const mockReader = {
           read: vi.fn().mockImplementation(async () => {
             readStep++;
             if (readStep === 1) {
               return {done: false, value: chunk1};
             } else if (readStep === 2) {
               return {done: false, value: chunk2};
             }
             return {done: true, value: undefined};
           }),
         };

         global.fetch = vi.fn()
                            .mockResolvedValueOnce({
                              ok: true,
                              status: 200,
                              json: async () => mockMeta,
                            })
                            .mockResolvedValueOnce({
                              ok: true,
                              status: 200,
                              headers: new Headers({'Content-Length': '8'}),
                              body: {
                                getReader: () => mockReader,
                              },
                            });

         const progressLoaded: number[] = [];
         const archive = await downloadGcsArchive(
             TARGET_GCS_ARCHIVE_URL,
             'test_token',
             (loaded) => {
               progressLoaded.push(loaded);
             },
         );

         expect(archive.url).toBe(TARGET_GCS_ARCHIVE_URL);
         expect(archive.filename)
             .toBe(
                 'archive_phone_20260331_streaming_md5.wprgo',
             );
         expect(archive.size).toBe(8);
         expect(archive.data).toEqual(new Uint8Array([1, 2, 3, 4, 5, 6, 7, 8]));
         expect(progressLoaded).toEqual([4, 8]);
       });

    it('throws immediately if fetchGcsMetadata fails', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        text: async () => 'Not found',
      });

      await expect(
          downloadGcsArchive(TARGET_GCS_ARCHIVE_URL, 'test_token'),
          )
          .rejects.toThrow(/Failed to fetch GCS metadata/);
    });

    it('throws immediately if metadata md5Hash is missing or empty',
       async () => {
         global.fetch = vi.fn().mockResolvedValue({
           ok: true,
           status: 200,
           json: async () => ({
             name: 'archive.wprgo',
             bucket: 'chrome-partner-loadline',
             size: '100',
             md5Hash: '',
           }),
         });

         await expect(
             downloadGcsArchive(TARGET_GCS_ARCHIVE_URL, 'test_token'),
             )
             .rejects.toThrow(/missing md5Hash/);
       });

    it('throws error when media download request fails', async () => {
      const mockMeta = {
        name: 'archive_phone_20260331.wprgo',
        bucket: 'chrome-partner-loadline',
        size: '8',
        md5Hash: 'hash8bytes',
      };

      global.fetch = vi.fn()
                         .mockResolvedValueOnce({
                           ok: true,
                           status: 200,
                           json: async () => mockMeta,
                         })
                         .mockResolvedValueOnce({
                           ok: false,
                           status: 403,
                           statusText: 'Forbidden',
                           text: async () => 'Access denied',
                         });

      await expect(
          downloadGcsArchive(TARGET_GCS_ARCHIVE_URL, 'test_token'),
          )
          .rejects.toThrow(
              /GCS download authorization error \(403 Forbidden\)/);
    });
  });
});
