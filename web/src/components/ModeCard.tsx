import type { ModeContract } from "../types";
import { ModeIcon } from "../icons";
import { useTilt } from "../useTilt";

// depth/intensity rises with mode caution: fast = light & shallow, extend = deep & full
const DEPTH: Record<string, number> = { fast: 5, normal: 7, extend: 10 };

export function ModeCard({
  m,
  selected,
  onPick,
}: {
  m: ModeContract;
  selected: boolean;
  onPick: () => void;
}) {
  const ref = useTilt<HTMLButtonElement>(DEPTH[m.mode] ?? 7);
  return (
    <button
      ref={ref}
      type="button"
      className={`mode-card mode-slab depth-${m.mode}`}
      data-mode={m.mode}
      aria-pressed={selected}
      onClick={onPick}
    >
      <div className="mc-head">
        <span className="glyph">
          <ModeIcon mode={m.mode} />
        </span>
        <div>
          <div className="mc-name">{m.mode}</div>
          <div className="mc-clock">clock · {m.primary_clock}</div>
        </div>
      </div>
      <dl>
        <dt>verifier</dt>
        <dd>{m.verifier_tier}</dd>
        <dt>detectors</dt>
        <dd>{m.detectors}</dd>
        <dt>ships</dt>
        <dd>{m.acceptable_grades.join(" · ")}</dd>
        <dt>hotspots</dt>
        <dd>{m.max_hotspots == null ? "all" : m.max_hotspots}</dd>
        <dt>z3</dt>
        <dd>{m.verifier_tier === "MICRO" ? "never" : m.verifier_tier === "FULL_CERT" ? "full" : "small regions"}</dd>
        <dt>latency</dt>
        <dd>{m.latency_budget_s == null ? "unbounded" : `≤ ${m.latency_budget_s}s`}</dd>
        <dt>posture</dt>
        <dd style={{ fontSize: 11 }}>{m.risk_posture}</dd>
      </dl>
      <div className="v-sub" style={{ marginTop: 2 }}>{m.stop_condition}</div>
    </button>
  );
}
