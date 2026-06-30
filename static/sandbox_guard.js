/* §BE TE-2 — ISOLATION GUARD (the security heart), main thread.
   ================================================================================================================
   Wraps the Pyodide Web Worker (runner.worker.js) in layered defence. User code may be malicious; every layer must
   hold:
     ★ structural   — Pyodide is a WASM browser sandbox: user code cannot reach our server (the worker has no path).
     ★ DOM isolation — execution is in a Worker: it cannot touch the page (an infinite loop won't freeze the UI).
     ★ timeout       — if the worker doesn't answer in `timeoutMs`, we worker.terminate() (kills the infinite loop)
                        and respawn a clean one. A worker cannot kill its own infinite loop — the main thread must.
     ★ network 0     — runner.worker.js severs fetch/XHR/WebSocket/importScripts after load; user code can't phone home.
     ★ key 0         — the payload we post to the browser is { code } ONLY. We assert it carries no secret (below).
     ★ untrusted out — the returned stdout/value is treated as untrusted: size-capped here, and the UI must render it
                        as TEXT (textContent), never innerHTML. No XSS surface.

   Honest caveat: a hard per-worker MEMORY cap is not portably observable from the main thread, so we do NOT claim one
   — a runaway allocation is bounded by the timeout (it also burns wall-clock) + the browser's own per-process limit +
   the output cap, and a worker that dies (OOM) is caught by onerror and surfaced. (See TESTENV_INDEX.md §4.)

   This file cannot be live-verified in our build sandbox (the Pyodide CDN is egress-blocked); the author validates the
   running behaviour on Render. */

"use strict";

(function (global) {
  const WORKER_URL = "/static/runner.worker.js";
  const OUTPUT_CAP = 100000;          // chars; output beyond this is dropped with a truncation marker
  const DEFAULT_TIMEOUT = 4000;       // ms; an unbounded loop is terminate()d after this
  const INIT_TIMEOUT = 30000;         // ms; first init downloads the Pyodide WASM (seconds) — generous, one-time

  // ★ key-0 guard: the ONLY thing allowed across to the browser worker is the code string. Any key/session-like field
  //   is a bug (keys live on the server). Throw rather than risk a leak.
  const SECRET_KEYS = ["key", "apikey", "api_key", "token", "session", "secret", "authorization", "auth", "password"];
  function assertNoSecrets(payload) {
    for (const k of Object.keys(payload)) {
      if (SECRET_KEYS.includes(k.toLowerCase())) {
        throw new Error("sandbox_guard refusing to send a secret to the browser: " + k);
      }
    }
  }

  function sanitizeOutput(s) {
    if (typeof s !== "string") return "";
    if (s.length <= OUTPUT_CAP) return s;
    return s.slice(0, OUTPUT_CAP) + "\n… [출력이 잘렸습니다 — output truncated at " + OUTPUT_CAP + " chars]";
  }

  class SandboxRunner {
    constructor() {
      this.worker = null;
      this.ready = null;       // Promise resolved when the worker has loaded Pyodide
      this._seq = 0;
    }

    _spawn() {
      this.worker = new Worker(WORKER_URL);
      this.ready = new Promise((resolve, reject) => {
        const id = ++this._seq;
        const to = setTimeout(() => { this._kill(); reject(new Error("Pyodide init timed out")); }, INIT_TIMEOUT);
        const onMsg = (e) => {
          if (e.data && e.data.type === "ready") {
            clearTimeout(to); this.worker.removeEventListener("message", onMsg); resolve();
          }
        };
        this.worker.addEventListener("message", onMsg);
        this.worker.addEventListener("error", () => { clearTimeout(to); reject(new Error("worker failed to load")); }, { once: true });
        this.worker.postMessage({ id, type: "init" });   // code-only protocol; no secret
      });
    }

    _kill() {
      if (this.worker) { try { this.worker.terminate(); } catch (_e) { /* noop */ } }
      this.worker = null; this.ready = null;
    }

    /** Warm the runtime (call on idle so the user's first real run is instant). */
    async warm() {
      if (!this.worker) this._spawn();
      try { await this.ready; return true; } catch (_e) { this._kill(); return false; }
    }

    /**
     * Run user code in the isolated worker.
     * @returns {Promise<{ok, stdout, value, error, killed, ms}>}  — strings are already sanitized & capped.
     */
    async runUserCode(code, opts) {
      opts = opts || {};
      const timeoutMs = opts.timeoutMs || DEFAULT_TIMEOUT;
      if (typeof code !== "string" || !code.trim()) return { ok: false, error: "no code to run" };

      if (!this.worker) this._spawn();
      try { await this.ready; } catch (e) { this._kill(); return { ok: false, error: "runtime unavailable: " + e.message }; }

      const id = ++this._seq;
      const payload = { id, type: "run", code };   // ← code ONLY
      assertNoSecrets(payload);                     // structural key-0 assertion

      const started = (global.performance && performance.now) ? performance.now() : 0;
      return await new Promise((resolve) => {
        const finish = (r) => {
          this.worker && this.worker.removeEventListener("message", onMsg);
          clearTimeout(to);
          r.ms = (global.performance && performance.now) ? Math.round(performance.now() - started) : 0;
          resolve(r);
        };
        const to = setTimeout(() => {
          // ★ the infinite-loop killer: the worker is unresponsive ⇒ terminate it and respawn a clean one.
          this._kill();
          finish({ ok: false, killed: true, error: "실행 시간 초과 — terminated after " + timeoutMs + "ms (무한루프 방어)" });
        }, timeoutMs);
        const onMsg = (e) => {
          const m = e.data || {};
          if (m.type !== "result" || m.id !== id) return;
          finish({
            ok: !!m.ok,
            stdout: sanitizeOutput(m.stdout || ""),
            value: sanitizeOutput(m.value || ""),
            error: m.error ? sanitizeOutput(m.error) : "",
          });
        };
        this.worker.addEventListener("message", onMsg);
        // if the worker dies mid-run (e.g. OOM), surface it instead of hanging
        this.worker.addEventListener("error", () => finish({ ok: false, error: "worker crashed (가능성: 메모리 초과)" }), { once: true });
        this.worker.postMessage(payload);
      });
    }
  }

  global.SandboxRunner = SandboxRunner;
})(typeof self !== "undefined" ? self : this);
