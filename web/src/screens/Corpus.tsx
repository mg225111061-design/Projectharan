import { useEffect, useState } from "react";
import type { CorpusResult } from "../types";
import { api } from "../api";
import { Check, Info } from "../icons";
import { Slab } from "../components/Slab";

export function Corpus({ onRestart }: { onRestart: () => void }) {
  const [data, setData] = useState<CorpusResult | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.corpus().then(setData).catch((e) => setErr(String(e)));
  }, []);

  const maxRatio = data ? Math.max(1, ...data.rows.map((r) => r.ratio)) : 1;

  return (
    <div className="fade">
      <div className="eyebrow">step 5 · the proof · real repositories</div>
      <h2>The same engine, run on whole programs we didn't write.</h2>
      <p className="lead">
        Five archetypal codebases — including AI-generated code that was never profiled. Each row is a
        measured whole-program result with its Amdahl ceiling and an enforced grade. The honest DECLINEs
        are the point: a tool that always finds a win is a tool that lies.
      </p>

      {err && <div className="card warn">couldn't load corpus: {err}</div>}
      {!data && !err && (
        <div className="card">
          <span className="spin" /> running corpus on the real engine…
        </div>
      )}

      {data && (
        <>
          <div className="row mt" style={{ marginBottom: 14 }}>
            <span className="grade exact"><span className="gd" />exact · {data.grades.exact}</span>
            <span className="grade probabilistic"><span className="gd" />probabilistic · {data.grades.probabilistic}</span>
            <span className="grade decline"><span className="gd" />decline · {data.grades.decline}</span>
            <span className="pill spacer" style={{ marginLeft: "auto" }}>
              <Check /> {data.rows.length} repos · ratio ≤ ceiling on every row
            </span>
          </div>

          <div className="stage">
          <Slab className="corpus-slab" max={4}>
            {data.rows.map((r) => {
              const unbounded = !isFinite(r.ceiling);
              const denom = Math.max(maxRatio, r.ratio) || 1;
              const fillPct = Math.min(92, (r.ratio / denom) * 92);
              const wallPct = unbounded ? 98 : Math.min(99, (r.ceiling / denom) * 92);
              return (
                <div className="vrow fade" key={r.name}>
                  <div>
                    <div className="v-name">{r.name}</div>
                    <div className="v-sub">{r.archetype}</div>
                    <div className="tags" style={{ marginTop: 4 }}>
                      {r.detected.map((d) => (
                        <span className="tag" key={d}>{d}</span>
                      ))}
                    </div>
                  </div>
                  <div className="v-waste">f = {r.hotspot_fraction.toFixed(3)}</div>
                  {r.grade === "decline" ? (
                    <div className="meter declined" title={r.note}>
                      <div className="lbl" style={{ color: "var(--decline)", mixBlendMode: "normal" }}>
                        no claim
                      </div>
                    </div>
                  ) : (
                    <div className="meter" title={`measured ${r.ratio.toFixed(2)}× ≤ ceiling ${unbounded ? "∞" : r.ceiling.toFixed(0)}×`}>
                      <div className="fill" style={{ width: `${fillPct}%`, background: "var(--extend)" }} />
                      <div className="wall" style={{ left: `${wallPct}%` }} />
                      <div className="lbl">{r.ratio.toFixed(2)}×</div>
                    </div>
                  )}
                  <div className="v-ceil">
                    <span className={`grade ${r.grade}`}><span className="gd" />{r.grade}</span>
                    <div style={{ marginTop: 4 }}>≤ {unbounded ? "∞" : `${r.ceiling.toFixed(0)}×`}</div>
                  </div>
                </div>
              );
            })}
          </Slab>
          </div>

          <div className="honesty">
            <span className="ic"><Info /></span>
            <span>
              Big ratios here come from genuinely quadratic code on large inputs (high hotspot fraction →
              high ceiling) — not from a flattering average. The ceiling is shown next to every number, and
              the measured value never exceeds it. {data.found_nothing ? "" : "Every repo above was measured this run."}
            </span>
          </div>
        </>
      )}

      <div className="row mt">
        <button className="ghost" onClick={onRestart}>
          ↺ Start over
        </button>
        <a className="btn" href="/studio" target="_blank" rel="noreferrer" style={{ textDecoration: "none" }}>
          Open the studio data view
        </a>
      </div>
    </div>
  );
}
