import type { ShippedRow } from "../types";
import { Slab } from "./Slab";

// THE signature object: one measured speedup, rendered as a floating dimensional slab. The measured-speedup
// bar and its Amdahl-ceiling marker live on a raised plane (translateZ) above the slab face — the fill can
// never cross the wall, so the object literally cannot show a claim larger than its ceiling.
export function SpeedupSlab({ row, mode }: { row: ShippedRow; mode: string }) {
  const unbounded = row.ceiling == null;
  const ceil = row.ceiling ?? row.ratio * 1.25;
  const denom = Math.max(ceil, row.ratio) || 1;
  const fillPct = Math.min(100, (row.ratio / denom) * 94);
  const wallPct = unbounded ? 99 : Math.min(99, (ceil / denom) * 94);
  return (
    <div className="stage">
      <Slab className="speed-slab" data-mode={mode} max={8}>
        <div className="plane ss-head" style={{ ["--z" as string]: "26px" }}>
          <span className="ss-waste">{row.waste_type}</span>
          <span className={`grade ${row.grade}`}>
            <span className="gd" />
            {row.grade}
          </span>
        </div>

        <div className="plane ss-meter" style={{ ["--z" as string]: "52px" }}>
          <div className="meter3">
            <div className="fill3" style={{ width: `${fillPct}%` }} />
            <div className="wall3" style={{ left: `${wallPct}%` }}>
              <span className="wall3-lbl">Amdahl ceiling {unbounded ? "∞" : `${ceil.toFixed(2)}×`}</span>
            </div>
            <div className="meter3-val">{row.ratio.toFixed(2)}×</div>
          </div>
        </div>

        <div className="plane ss-read" style={{ ["--z" as string]: "20px" }}>
          <div className="ss-kv">
            <span className="ss-k">measured whole-program</span>
            <span className="ss-v">{row.ratio.toFixed(3)}×</span>
          </div>
          <div className="ss-kv">
            <span className="ss-k">hotspot fraction f</span>
            <span className="ss-v">{row.hotspot_fraction.toFixed(3)}</span>
          </div>
          <div className="ss-kv">
            <span className="ss-k">ceiling 1/(1−f)</span>
            <span className="ss-v">{unbounded ? "∞" : `${ceil.toFixed(2)}×`}</span>
          </div>
        </div>
      </Slab>
    </div>
  );
}
