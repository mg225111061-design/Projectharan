import type { ShippedRow } from "../types";

// The cumulative compounding curve: each shipped fix's `ratio` is the FRESH whole-program ratio measured with
// all fixes up to that point active (never a product-of-locals). We draw it rising from the 1.0× baseline — a
// dimensional readout of how the verified wins compound. Real engine data only.
export function CompoundCurve({ shipped, cumulative, mode }: {
  shipped: ShippedRow[];
  cumulative: number;
  mode: string;
}) {
  if (shipped.length === 0) return null;
  const pts = [1.0, ...shipped.map((s) => s.ratio)];
  const W = 520, H = 150, padX = 34, padY = 18;
  const maxY = Math.max(...pts) * 1.08;
  const minY = 1.0;
  const x = (i: number) => padX + (i / (pts.length - 1 || 1)) * (W - padX * 2);
  const y = (v: number) => H - padY - ((v - minY) / (maxY - minY || 1)) * (H - padY * 2);
  const line = pts.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const area = `${line} L${x(pts.length - 1).toFixed(1)},${(H - padY).toFixed(1)} L${x(0).toFixed(1)},${(H - padY).toFixed(1)} Z`;

  return (
    <div className="stage">
      <div className="slab curve-slab" data-mode={mode}>
        <div className="ss-head" aria-hidden="true" style={{ marginBottom: 8 }}>
          <span className="ss-waste">cumulative compounding · measured fresh</span>
          <span className="mono" style={{ fontSize: 18, fontWeight: 500 }}>{cumulative.toFixed(3)}×</span>
        </div>
        <svg className="curve" viewBox={`0 0 ${W} ${H}`} width="100%" role="img"
             aria-label={`Cumulative whole-program speedup compounds to ${cumulative.toFixed(2)} times over ${shipped.length} verified fixes, measured fresh.`}>
          <line x1={padX} y1={H - padY} x2={W - padX} y2={H - padY} className="curve-axis" />
          <line x1={padX} y1={y(1.0)} x2={W - padX} y2={y(1.0)} className="curve-base" />
          <path d={area} className="curve-area" />
          <path d={line} className="curve-line" />
          {pts.map((v, i) => (
            <g key={i}>
              <circle cx={x(i)} cy={y(v)} r={3.2} className="curve-dot" />
              {i > 0 && (
                <text x={x(i)} y={y(v) - 8} className="curve-lbl" textAnchor="middle">{v.toFixed(2)}×</text>
              )}
            </g>
          ))}
          <text x={padX} y={H - 4} className="curve-axlbl">baseline 1.00×</text>
          <text x={W - padX} y={H - 4} className="curve-axlbl" textAnchor="end">{shipped.length} fixes</text>
        </svg>
      </div>
    </div>
  );
}
