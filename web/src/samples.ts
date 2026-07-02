// Sample snippets that exercise the engine's real AST detectors (list_as_set, n_plus_1,
// accidental_quadratic, algo_replace/strength-reduction, simd_offload). Pasting these makes the
// detector → measured-result path light up with honest grades.
export const SAMPLES: { label: string; code: string }[] = [
  {
    label: "N+1 fetch in a loop",
    code: `def enrich(order_ids, allowed):
    rows = []
    for oid in order_ids:
        if oid in allowed:          # 'allowed' is a list → O(n) membership
            user = fetch_user(oid)  # per-item fetch → N+1
            rows.append((oid, user))
    return rows`,
  },
  {
    label: "Accidental O(n²) build",
    code: `def build_report(events):
    report = ""
    for e in events:
        report = report + format_line(e)   # string += in a loop → O(n²)
    seen = []
    for e in events:
        if e.id in seen:                   # membership over a growing list
            continue
        seen.append(e.id)
    return report`,
  },
  {
    label: "Scalar math over a list (vectorizable)",
    code: `import math

def features(samples):
    out = []
    for x in samples:
        out.append(math.sqrt(x) * 2 + math.sin(x))  # scalar math.* per element
    energy = sum(v ** 2 for v in out)               # x**2 → strength-reducible
    return out, energy`,
  },
  {
    label: "Clean code (expect honest DECLINE)",
    code: `def total(prices):
    # already linear, nothing wasteful to fix
    return sum(prices)`,
  },
];
