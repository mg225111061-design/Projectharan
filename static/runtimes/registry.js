/* §BG LANG-1 — multi-language WASM runtime registry (browser-side, §BE-isolated).
   ================================================================================================================
   Maps a language → its in-browser WASM runtime, with ★HONEST labels (maturity + download size). No exaggeration:
   compiled languages (Rust/C/C++) reach near-native in WASM; Go via TinyGo is a *subset*; Python (Pyodide) works but
   is bulky + clunky for C-extensions; Ruby is improving; Java/Kotlin are immature in-browser. Every runtime runs
   inside the §BE Web-Worker sandbox (network severed, key-0, timeout→terminate, output sanitized).

   ★ Honest ceiling (research): WASM is ~1.5–2× slower than native (a structural ceiling) — this is NEAR-native, not
   past-native. The *past-native* win is fold (server `/api/check` removes the loop entirely); see ACCEL-5 below.
   ★ Sandbox here blocks the CDNs, so this is author-validated on Render — no false "verified" claim. */

"use strict";

(function (global) {
  // tier: "native-class" (compiled, near-native) | "subset" | "works-bulky" | "improving" | "immature"
  const RUNTIMES = {
    python:       { label: "Python (Pyodide)", tier: "works-bulky", approxMB: 6.5, kind: "interpreter",
                    note: "성숙하지만 무겁다(수 MB) · 순수 파이썬은 OK · C-확장은 수동/제한", worker: "/static/runner.worker.js" },
    javascript:   { label: "JavaScript (native)", tier: "native-class", approxMB: 0, kind: "native",
                    note: "브라우저 네이티브 — WASM 불필요", worker: null },
    c:            { label: "C (Emscripten/clang→wasm)", tier: "native-class", approxMB: 1.5, kind: "compiled",
                    note: "near-native · SIMD(-msimd128)/threads(-pthread) 가능", worker: null },
    cpp:          { label: "C++ (Emscripten)", tier: "native-class", approxMB: 1.8, kind: "compiled",
                    note: "near-native · 표준 라이브러리 크기 주의", worker: null },
    rust:         { label: "Rust (wasm-pack/wasm32)", tier: "native-class", approxMB: 0.6, kind: "compiled",
                    note: "near-native · 작은 산출물 · SIMD 가능", worker: null },
    assemblyscript:{label: "AssemblyScript", tier: "native-class", approxMB: 0.1, kind: "compiled",
                    note: "TS-유사 문법 → 작고 빠른 wasm", worker: null },
    go:           { label: "Go (TinyGo)", tier: "subset", approxMB: 2.0, kind: "compiled",
                    note: "★TinyGo는 표준 Go의 *부분집합* (전체 Go 런타임은 ~2MB+ GC, 무겁다)", worker: null },
    lua:          { label: "Lua (wasmoon)", tier: "native-class", approxMB: 0.4, kind: "interpreter",
                    note: "작고 빠른 임베디드 인터프리터", worker: null },
    sqlite:       { label: "SQLite (sql.js / wa-sqlite)", tier: "native-class", approxMB: 1.0, kind: "engine",
                    note: "WASM SQLite — 쿼리 전용", worker: null },
    ruby:         { label: "Ruby (ruby.wasm)", tier: "improving", approxMB: 7.0, kind: "interpreter",
                    note: "개선 중 · 크고 일부 거칠다", worker: null },
    php:          { label: "PHP (php-wasm)", tier: "improving", approxMB: 4.0, kind: "interpreter",
                    note: "동작하나 미성숙 · 확장 제한", worker: null },
    java:         { label: "Java/Kotlin (TeaVM/CheerpJ)", tier: "immature", approxMB: 0, kind: "compiled",
                    note: "★in-browser 미성숙 — 권장하지 않음(정직)", worker: null, unavailable: true },
  };

  function get(lang) { return RUNTIMES[(lang || "").toLowerCase()] || null; }

  // honest, user-facing one-liner for the UI
  function describe(lang) {
    const r = get(lang);
    if (!r) return { ok: false, text: `'${lang}'은(는) 등록된 브라우저 런타임이 없습니다.` };
    if (r.unavailable) return { ok: false, text: `${r.label}: ${r.note}` };
    const size = r.approxMB ? ` · 첫 로드 ~${r.approxMB}MB (이후 IndexedDB 캐시로 즉시)` : "";
    const tierKo = { "native-class": "네이티브급", "subset": "부분집합", "works-bulky": "동작(무거움)",
                     "improving": "개선중", "immature": "미성숙" }[r.tier] || r.tier;
    return { ok: true, text: `${r.label} — ${tierKo}${size}. ${r.note}`, runtime: r };
  }

  function languages() { return Object.keys(RUNTIMES); }

  global.HaranRuntimes = { RUNTIMES, get, describe, languages };
})(typeof self !== "undefined" ? self : this);
