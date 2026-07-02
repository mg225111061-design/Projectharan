/* §BG ACCEL-3 — compiled-WASM IndexedDB cache (the biggest felt win: 2nd load is instant).
   ================================================================================================================
   A multi-MB runtime (Pyodide ~6.5MB, ruby.wasm ~7MB) costs seconds to download+compile on the FIRST load. We store
   the COMPILED `WebAssembly.Module` (structured-clonable in modern browsers) in IndexedDB keyed by (url, version),
   so every later load is a near-instant cache hit — no re-download, no re-compile. Honest: the first load is still
   heavy (download is download); we remove only the *repeat* cost. This is near-native plumbing, NOT magic speed.

   ★ Sandbox here blocks the CDNs and IndexedDB isn't exercised in this build → author-validated on Render.
   Falls back gracefully to a plain streaming compile when IndexedDB or Module-caching is unavailable. */

"use strict";

(function (global) {
  const DB = "haran_wasm_cache", STORE = "modules", VERSION = 1;

  function _open() {
    return new Promise((resolve, reject) => {
      if (!global.indexedDB) return reject(new Error("no IndexedDB"));
      const req = global.indexedDB.open(DB, VERSION);
      req.onupgradeneeded = () => { const db = req.result; if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE); };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error || new Error("IndexedDB open failed"));
    });
  }
  function _tx(db, mode) { return db.transaction(STORE, mode).objectStore(STORE); }
  function _get(store, key) { return new Promise((res, rej) => { const r = store.get(key); r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error); }); }
  function _put(store, key, val) { return new Promise((res, rej) => { const r = store.put(val, key); r.onsuccess = () => res(true); r.onerror = () => rej(r.error); }); }

  /** Compile a WASM url to a WebAssembly.Module, caching the compiled Module in IndexedDB by (url, version).
   *  @returns {Promise<{module: WebAssembly.Module, cached: boolean}>} */
  async function cachedCompile(url, version) {
    const key = `${url}@@${version || "v1"}`;
    // 1) try the cache (a compiled Module is structured-clonable in Chrome/Firefox)
    try {
      const db = await _open();
      const hit = await _get(_tx(db, "readonly"), key);
      if (hit instanceof global.WebAssembly.Module) return { module: hit, cached: true };
    } catch (_e) { /* fall through to fetch */ }
    // 2) miss → streaming compile (compiles WHILE downloading)
    let module;
    if (global.WebAssembly.compileStreaming) {
      module = await global.WebAssembly.compileStreaming(fetch(url));
    } else {
      const buf = await (await fetch(url)).arrayBuffer();
      module = await global.WebAssembly.compile(buf);
    }
    // 3) store for next time (best-effort; a browser that can't clone a Module just won't cache)
    try { const db = await _open(); await _put(_tx(db, "readwrite"), key, module); } catch (_e) { /* non-fatal */ }
    return { module, cached: false };
  }

  async function clear() {
    try { const db = await _open(); await new Promise((res) => { const r = _tx(db, "readwrite").clear(); r.onsuccess = res; r.onerror = res; }); return true; }
    catch (_e) { return false; }
  }

  global.HaranWasmCache = { cachedCompile, clear };
})(typeof self !== "undefined" ? self : this);
