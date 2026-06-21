import type { ModeContract, ModeId } from "../types";
import { ModeCard } from "../components/ModeCard";
import { Arrow } from "../icons";

export function ModeSelect({
  modes,
  picked,
  onPick,
  onNext,
}: {
  modes: ModeContract[];
  picked: ModeId | null;
  onPick: (m: ModeId) => void;
  onNext: () => void;
}) {
  return (
    <div className="fade">
      <div className="eyebrow">step 1 · pick a contract</div>
      <h2>How cautious should the verifier be?</h2>
      <p className="lead">
        The mode is not a speed knob — it's a contract. It fixes which verifier tier runs, which grades are
        allowed to ship, how many hotspots get attacked, and when to stop. The accent color follows your
        choice through the rest of the flow.
      </p>

      <div className="grid cols-3 mt">
        {modes.map((m) => (
          <ModeCard key={m.mode} m={m} selected={picked === m.mode} onPick={() => onPick(m.mode)} />
        ))}
      </div>

      {picked && (
        <div className="card mt fade" data-mode={picked}>
          <div className="row">
            <span className="grade exact" style={{ background: "var(--accent-tint)", color: "var(--accent-deep)" }}>
              {picked} selected
            </span>
            <span className="muted">
              {picked === "fast" && "Never reaches Z3. Top hotspots only. Ships the first real win and gets out of your way."}
              {picked === "normal" && "Cheap certificates on small regions. Compounds real wins until they stop paying off."}
              {picked === "extend" && "Full Z3 translation validation. EXACT or it declines. Time is no object; correctness is."}
            </span>
            <button className="btn spacer" style={{ marginLeft: "auto" }} onClick={onNext}>
              Choose provider <Arrow />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
