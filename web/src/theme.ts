// A1 — the mode color switch. A single `mode` drives a CSS-variable theme that re-themes the WHOLE app:
// every element using var(--accent) (header band, speedup-bar fills, focus rings, key accents) recolors at
// once. Mode = temperature: fast→cyan, normal→amber, extend→violet. applyMode sets both data-mode (CSS
// cascade) and the --accent vars directly on the root, so the switch is robust AND unit-testable in node.
export type ModeId = "fast" | "normal" | "extend";

export const MODE_ACCENT: Record<ModeId, string> = {
  fast: "#0E9FB5",   // cyan
  normal: "#BA7517", // amber
  extend: "#534AB7", // violet
};

export const MODE_ACCENT_DEEP: Record<ModeId, string> = {
  fast: "#0B5566",
  normal: "#633806",
  extend: "#26215C",
};

export const MODE_ACCENT_TINT: Record<ModeId, string> = {
  fast: "#E4F6F9",
  normal: "#FAEEDA",
  extend: "#EEEDFE",
};

// Apply a mode to an element (the app root). Sets data-mode for the CSS cascade and writes the accent vars
// explicitly so the whole interface re-themes instantly. Returns the accent (handy for tests).
export function applyMode(el: { setAttribute: (k: string, v: string) => void; style: { setProperty: (k: string, v: string) => void } }, mode: ModeId): string {
  el.setAttribute("data-mode", mode);
  el.style.setProperty("--accent", MODE_ACCENT[mode]);
  el.style.setProperty("--accent-deep", MODE_ACCENT_DEEP[mode]);
  el.style.setProperty("--accent-tint", MODE_ACCENT_TINT[mode]);
  return MODE_ACCENT[mode];
}

// The three accents are distinct by construction (asserted in test_theme).
export function distinctAccents(): boolean {
  const s = new Set(Object.values(MODE_ACCENT));
  return s.size === 3;
}
