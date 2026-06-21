// A2 — the signature speedup slab geometry. The measured-speedup bar (fill) and the Amdahl-ceiling marker
// (wall) are computed here so the invariant is unit-testable: because the engine guarantees ratio ≤ ceiling,
// the fill can NEVER cross the wall. fillPct is driven by ratio, wallPct by the ceiling; both share a denom.
export function slabGeometry(ratio: number, ceiling: number | null) {
  const unbounded = ceiling == null || !isFinite(ceiling);
  const ceil = unbounded ? ratio * 1.25 : (ceiling as number);
  const denom = Math.max(ceil, ratio) || 1;
  const fillPct = Math.min(100, (ratio / denom) * 94);
  const wallPct = unbounded ? 99 : Math.min(99, (ceil / denom) * 94);
  return { unbounded, ceil, fillPct, wallPct };
}

// round a measured number for display (no float artifacts) — used everywhere a ratio/f/ceiling is shown
export function r3(x: number): string {
  return Number(x).toFixed(3);
}
export function r2(x: number | null): string {
  return x == null || !isFinite(x as number) ? "∞" : Number(x).toFixed(2);
}
