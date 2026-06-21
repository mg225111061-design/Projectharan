import type { Demo, ShippedRow } from "../types";
import { Arrow, Check } from "../icons";
import { SpeedupSlab } from "../components/SpeedupSlab";

export function Landing({ demo, onStart }: { demo: Demo | null; onStart: () => void }) {
  const totalDetectors = demo ? Math.max(...demo.modes.map((m) => m.detectors)) : 40;
  // the hero IS the thesis: one real measured speedup as a floating dimensional object (prefer an EXACT win)
  const heroRun = demo?.runs.find((r) => r.shipped.length) ?? null;
  const heroRow: ShippedRow | null = heroRun
    ? heroRun.shipped.find((s) => s.grade === "exact") ?? heroRun.shipped[0]
    : null;

  return (
    <div className="fade">
      <section className="hero">
        <div className="hero-copy">
          <div className="eyebrow">whole-program · measured · Amdahl-honest</div>
          <h1>A speedup you can trust — because a verifier, not the model, decides what ships.</h1>
          <p className="lead mt">
            Paste your code. Pick how cautious to be. MR.JEFFREY profiles it, proposes fixes, and{" "}
            <strong>measures the whole program</strong> before and after. Every win carries the hotspot
            fraction it came from and its Amdahl ceiling — and the measured number can never cross that
            ceiling. No win, no claim.
          </p>
          <div className="row mt">
            <button className="btn lg" onClick={onStart}>
              Paste your code <Arrow />
            </button>
            <span className="pill"><Check /> {totalDetectors} verified detectors</span>
          </div>
        </div>
        <div className="hero-object">
          {heroRow && heroRun ? (
            <SpeedupSlab row={heroRow} mode={heroRun.mode} />
          ) : (
            <div className="slab speed-slab" style={{ minHeight: 220 }} />
          )}
          {heroRow && (
            <div className="hero-cap">
              measured whole-program · {heroRun!.mode} mode · grade {heroRow.grade} · ratio ≤ ceiling
            </div>
          )}
        </div>
      </section>

      <div className="grid cols-3">
        <div className="card mb0">
          <h3>Measured, not estimated</h3>
          <p className="mb0">
            Speedups are timed end-to-end with warmup and best-of-k. A fast kernel that doesn't move the
            whole program doesn't count.
          </p>
        </div>
        <div className="card mb0">
          <h3>Amdahl honesty</h3>
          <p className="mb0">
            Each result shows the hotspot fraction <span className="mono">f</span> and the ceiling{" "}
            <span className="mono">1/(1−f)</span>. The bar's fill can't pass the wall.
          </p>
        </div>
        <div className="card mb0">
          <h3>Grades, enforced</h3>
          <p className="mb0">
            <span className="grade exact"><span className="gd" />exact</span>{" "}
            <span className="grade probabilistic"><span className="gd" />probabilistic</span>{" "}
            <span className="grade decline"><span className="gd" />decline</span> — proven, tested, or
            honestly nothing.
          </p>
        </div>
      </div>

      {demo && (
        <div className="card mt">
          <div className="eyebrow">three modes, three contracts</div>
          <div className="grid cols-3">
            {demo.modes.map((m) => (
              <div key={m.mode} data-mode={m.mode} className="mode-card" style={{ cursor: "default" }}>
                <div className="mc-head">
                  <span className="glyph" />
                  <div>
                    <div className="mc-name">{m.mode}</div>
                    <div className="mc-clock">{m.verifier_tier}</div>
                  </div>
                </div>
                <div className="v-sub">{m.stop_condition}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="honesty">
        <span className="ic"><Check /></span>
        <span>
          Your API key is held in this browser tab only — never written to disk, never logged, never sent
          anywhere except the provider you choose. We don't claim 50–100× averages; we claim exactly what
          we measured on your workload, bounded by Amdahl.
        </span>
      </div>
    </div>
  );
}
