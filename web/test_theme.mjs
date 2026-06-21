// A1 verification (node, no browser): the mode color switch produces three DISTINCT live accent values
// (fast=cyan, normal=amber, extend=violet) and applyMode actually changes the theme variable on selection.
import esbuild from "esbuild";
import { readFileSync } from "node:fs";

const src = readFileSync(new URL("./src/theme.ts", import.meta.url), "utf8");
const js = esbuild.transformSync(src, { loader: "ts", format: "esm" }).code;
const m = await import("data:text/javascript," + encodeURIComponent(js));

const eq = (a, b, msg) => { if (a !== b) { console.error("FAIL:", msg, "got", a, "want", b); process.exit(1); } };

// exact spec colours
eq(m.MODE_ACCENT.fast, "#0E9FB5", "fast → cyan");
eq(m.MODE_ACCENT.normal, "#BA7517", "normal → amber");
eq(m.MODE_ACCENT.extend, "#534AB7", "extend → violet");

// three DISTINCT live accent values
if (!m.distinctAccents()) { console.error("FAIL: accents not distinct"); process.exit(1); }
eq(new Set(Object.values(m.MODE_ACCENT)).size, 3, "3 distinct accents");

// the theme variable actually CHANGES on selection (re-themes the whole app via the root vars)
const mkEl = () => ({ attrs: {}, vars: {}, setAttribute(k, v) { this.attrs[k] = v; }, style: { setProperty(k, v) { /* bound below */ } } });
function probe(mode) {
  const el = { attrs: {}, vars: {} };
  el.setAttribute = (k, v) => (el.attrs[k] = v);
  el.style = { setProperty: (k, v) => (el.vars[k] = v) };
  const accent = m.applyMode(el, mode);
  return { el, accent };
}
const f = probe("fast"), n = probe("normal"), x = probe("extend");
eq(f.el.attrs["data-mode"], "fast", "data-mode set");
eq(f.el.vars["--accent"], "#0E9FB5", "fast --accent var");
eq(n.el.vars["--accent"], "#BA7517", "normal --accent var");
eq(x.el.vars["--accent"], "#534AB7", "extend --accent var");
// switching on the SAME element changes the var (the whole-app re-theme)
const one = { attrs: {}, vars: {} };
one.setAttribute = (k, v) => (one.attrs[k] = v);
one.style = { setProperty: (k, v) => (one.vars[k] = v) };
m.applyMode(one, "fast"); const before = one.vars["--accent"];
m.applyMode(one, "extend"); const after = one.vars["--accent"];
if (before === after) { console.error("FAIL: theme var did not change on selection"); process.exit(1); }
eq(before, "#0E9FB5", "before=fast"); eq(after, "#534AB7", "after=extend");

console.log("PASS test_theme — 3 distinct accents (fast=cyan #0E9FB5, normal=amber #BA7517, extend=violet #534AB7); applyMode re-themes the root and the --accent var changes on selection (whole-app switch).");
void mkEl;
