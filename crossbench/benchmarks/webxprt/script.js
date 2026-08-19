// Copyright 2026 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

return (async () => {
  // Wrapper for IDB
  const readStore = (dbName, storeName) => {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(dbName);

      request.onerror = () => reject(`Failed to open ${dbName}`);

      request.onsuccess = (event) => {
        const db = event.target.result;

        // Check if the store exists before trying to read it
        if (!db.objectStoreNames.contains(storeName)) {
          reject(`Store "${storeName}" not found. Available`
            + ` stores: ${[...db.objectStoreNames].join(', ')}`);
          return;
        }

        const transaction = db.transaction(storeName, "readonly");
        const store = transaction.objectStore(storeName);
        const dataReq = store.getAll();

        dataReq.onsuccess = () => {
          db.close();
          resolve(dataReq.result);
        }
        dataReq.onerror = () => {
          db.close();
          reject(`Failed to read from ${storeName}`);
        }
      };
    });
  };
  let url = new URL(document.location.href);
  let testName = url.searchParams.get("tName") || "";
  let tests = await readStore("wx5db", "tests");
  let workloads = await readStore("wx5db", "workloads");
  return JSON.stringify({
    url: url,
    name: testName,
    tests: tests.filter(t => t.testname === testName),
    workloads: workloads.filter(t => t.testname === testName),
  });
})();