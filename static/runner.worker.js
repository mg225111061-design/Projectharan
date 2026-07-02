/* §BE TE-1 — BROWSER EXECUTION inside a Web Worker (Pyodide / WASM Python).
   ================================================================================================================
   WHY this is structurally safe: Pyodide runs in the browser's WASM sandbox — by design it CANNOT reach our server.
   A Web Worker adds a second wall: this code has no DOM and no access to the page, so a user's infinite loop or
   runaway allocation cannot freeze the UI. The hard timeout is owned by the MAIN thread (sandbox_guard.js), which
   terminate()s this worker — a worker cannot reliably kill its own infinite loop.

   Heavy execution lives HERE (the user's CPU), not on Render's weak free tier. This is offload + isolation, NOT
   "ultra-speed" — a classical CPU is a classical CPU.

   Protocol (postMessage):
     in : {id, type:"init"}            -> {id, type:"ready"}            (load Pyodide once, then sever the network)
     in : {id, type:"run", code}       -> {id, type:"result", ok, stdout, value, error}
   The message NEVER contains an API key or session — the guard sends code only. */

"use strict";

// Pin a known-good Pyodide; the author may bump this in deployment. (CDN fetch is blocked in our build sandbox, so
// this path is author-validated on Render — see TESTENV_INDEX.md; no false "verified" claim is made here.)
const PYODIDE_VERSION = "0.26.2";
const PYODIDE_BASE = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

let pyodide = null;
let netSevered = false;

// ★ Sever the network INSIDE the worker, AFTER Pyodide has finished loading (Pyodide needs fetch/importScripts to
//   load its own WASM; user code, which runs strictly after, does not). Once removed, `import js; js.fetch(...)`,
//   `pyodide.http.pyfetch`, XHR, WebSocket and dynamic importScripts all fail — user code cannot phone home.
function severNetwork() {
  if (netSevered) return;
  const kill = (name) => {
    try {
      Object.defineProperty(self, name, {
        value: undefined, writable: false, configurable: false,
      });
    } catch (_e) { /* some are non-configurable already — fine */ }
  };
  ["fetch", "XMLHttpRequest", "WebSocket", "EventSource", "Request", "Response",
   "importScripts", "navigator"].forEach(kill);
  netSevered = true;
}

async function init(id) {
  if (pyodide) { postMessage({ id, type: "ready" }); return; }
  // eslint-disable-next-line no-undef
  importScripts(PYODIDE_BASE + "pyodide.js");
  // eslint-disable-next-line no-undef
  pyodide = await loadPyodide({ indexURL: PYODIDE_BASE });
  severNetwork();                                  // ← no network for any user code that follows
  postMessage({ id, type: "ready" });
}

async function run(id, code) {
  if (!pyodide) { postMessage({ id, type: "result", ok: false, error: "runtime not initialized" }); return; }
  let stdout = "";
  const cap = 200000;                              // hard output cap inside the worker too (defence in depth)
  const sink = (s) => { if (stdout.length < cap) stdout += s; };
  try {
    pyodide.setStdout({ batched: sink });
    pyodide.setStderr({ batched: sink });
    // Run user code in a FRESH namespace each time (no state bleed between runs).
    const ns = pyodide.toPy({});
    const value = await pyodide.runPythonAsync(code, { globals: ns });
    let valStr = "";
    try { valStr = value === undefined || value === null ? "" : String(value); } catch (_e) { valStr = ""; }
    postMessage({
      id, type: "result", ok: true,
      stdout: stdout.slice(0, cap),
      value: valStr.slice(0, cap),
    });
  } catch (err) {
    postMessage({ id, type: "result", ok: false, stdout: stdout.slice(0, cap), error: String(err && err.message || err) });
  } finally {
    try { pyodide.setStdout({}); pyodide.setStderr({}); } catch (_e) { /* noop */ }
  }
}

self.onmessage = (e) => {
  const m = e.data || {};
  if (m.type === "init") return void init(m.id);
  if (m.type === "run") return void run(m.id, typeof m.code === "string" ? m.code : "");
};
