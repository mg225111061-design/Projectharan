// A2/A4 verification (node, no browser): the signature slab's fill NEVER crosses the Amdahl wall (because
// the engine guarantees ratio ≤ ceiling), and displayed numbers are rounded (no float artifacts).
import esbuild from "esbuild";
import { readFileSync } from "node:fs";

async function load(rel) {
  const src = readFileSync(new URL(rel, import.meta.url), "utf8");
  const js = esbuild.transformSync(src, { loader: "ts", format: "esm" }).code;
  return import("data:text/javascript," + encodeURIComponent(js));
}
const fail = (m) => { console.error("FAIL:", m); process.exit(1); };

const M = await load("./src/meter.ts");

// fill ≤ wall for every (ratio ≤ ceiling) — the bar can never claim past its Amdahl ceiling
let checked = 0;
for (let f = 0.05; f < 0.999; f += 0.013) {
  const ceiling = 1 / (1 - f);
  // sweep ratios from ~1 up to the ceiling (engine guarantees ratio ≤ ceiling)
  for (let ratio = 1.0; ratio <= ceiling + 1e-9; ratio += Math.max(0.05, ceiling / 20)) {
    const g = M.slabGeometry(ratio, ceiling);
    if (g.fillPct > g.wallPct + 1e-9) fail(`fill ${g.fillPct} > wall ${g.wallPct} at ratio=${ratio} ceiling=${ceiling}`);
    checked++;
  }
}
// equal case (ratio == ceiling): fill at the wall, not past it
{ const g = M.slabGeometry(5, 5); if (g.fillPct > g.wallPct + 1e-9) fail("ratio==ceiling crossed"); }
// unbounded ceiling: wall at 99, fill ≤ 100 but driven by ratio*1.25 denom → fill ≤ wall region
{ const g = M.slabGeometry(1000, null); if (!g.unbounded) fail("unbounded not flagged"); if (g.fillPct > g.wallPct + 1e-9) fail("unbounded fill>wall"); }

// rounding: no float artifacts
if (M.r3(1.2649999) !== "1.265") fail("r3 round");
if (M.r2(5.299) !== "5.30") fail("r2 round");
if (M.r2(Infinity) !== "∞") fail("r2 inf");
if (M.r2(null) !== "∞") fail("r2 null");

console.log(`PASS test_ui — slab fill ≤ Amdahl wall on ${checked} (ratio≤ceiling) points incl. equality & unbounded (the bar never crosses the wall); displayed numbers rounded (no float artifacts).`);
