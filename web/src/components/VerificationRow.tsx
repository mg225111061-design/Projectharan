// The signature element. A measured whole-program speedup, drawn so the fill (ratio) can never pass the
// wall (Amdahl ceiling) — the row literally cannot lie about the ceiling. Grade sets the loudness.
import type { DeclinedRow, Grade, ShippedRow } from "../types";

function gradeFromReason(): Grade {
  return "decline";
}

export function ShippedVRow({ row, max }: { row: ShippedRow; max: number }) {
  const ceil = row.ceiling ?? row.ratio * 1.25; // unbounded → draw a generous wall beyond the fill
  const unbounded = row.ceiling == null;
  // scale the track so the largest ceiling on screen fills ~92% of the bar
  const denom = Math.max(max, ceil, row.ratio) || 1;
  const fillPct = Math.min(100, (row.ratio / denom) * 92);
  const wallPct = unbounded ? 98 : Math.min(99, (ceil / denom) * 92);
  return (
    <div className="vrow fade">
      <div>
        <div className="v-name">{row.name}</div>
        <div className="v-sub">
          hotspot fraction f = <span className="num">{row.hotspot_fraction.toFixed(3)}</span>
        </div>
      </div>
      <div className="v-waste">{row.waste_type}</div>
      <div className="meter" title={`measured ${row.ratio.toFixed(3)}× ≤ ceiling ${unbounded ? "∞" : ceil.toFixed(2)}×`}>
        <div className="fill" style={{ width: `${fillPct}%` }} />
        <div className="wall" style={{ left: `${wallPct}%` }} />
        <div className="lbl">{row.ratio.toFixed(3)}×</div>
      </div>
      <div className="v-ceil">
        <span className={`grade ${row.grade}`}>
          <span className="gd" />
          {row.grade}
        </span>
        <div style={{ marginTop: 4 }}>
          ≤ {unbounded ? "∞" : `${ceil.toFixed(2)}×`}
        </div>
      </div>
    </div>
  );
}

export function DeclinedVRow({ row }: { row: DeclinedRow }) {
  const g = gradeFromReason();
  return (
    <div className="vrow declined fade">
      <div>
        <div className="v-name">{row.name}</div>
        <div className="v-sub">{row.reason}</div>
      </div>
      <div className="v-waste">{row.waste_type}</div>
      <div className="meter" title="declined — nothing shipped">
        <div className="lbl" style={{ color: "var(--decline)", mixBlendMode: "normal" }}>
          no claim
        </div>
      </div>
      <div className="v-ceil">
        <span className={`grade ${g}`}>
          <span className="gd" />
          decline
        </span>
      </div>
    </div>
  );
}
