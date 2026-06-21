import type { OptimizeResult } from "../types";
import { DeclinedVRow } from "../components/VerificationRow";
import { SpeedupSlab } from "../components/SpeedupSlab";
import { Arrow, Check, Info } from "../icons";

export function Verification({
  result,
  onAgain,
  onCorpus,
}: {
  result: OptimizeResult;
  onAgain: () => void;
  onCorpus: () => void;
}) {
  const nothing = result.shipped.length === 0 && result.declined.length === 0;

  return (
    <div className="fade" data-mode={result.mode}>
      <div className="eyebrow">step 4 · verification panel · {result.mode} contract</div>
      <h2>What the verifier let through.</h2>

      <div className="grid cols-3 mt">
        <div className="card mb0">
          <div className="eyebrow">cumulative whole-program</div>
          <div style={{ fontSize: 30, fontWeight: 500 }} className="num">
            {result.cumulative_ratio.toFixed(3)}×
          </div>
          <div className="v-sub">re-measured fresh, all fixes active</div>
        </div>
        <div className="card mb0">
          <div className="eyebrow">verifier work</div>
          <div className="kv mt">
            <dt>z3 calls</dt>
            <dd>{result.z3_calls}</dd>
            <dt>complexity sweep</dt>
            <dd>{result.ran_complexity_sweep ? "yes" : "no"}</dd>
            <dt>latency</dt>
            <dd>{result.latency_ms != null ? `${result.latency_ms} ms` : "—"}</dd>
            <dt>tier</dt>
            <dd>{result.policy.verifier_tier}</dd>
          </div>
        </div>
        <div className="card mb0">
          <div className="eyebrow">detected in your code</div>
          {result.detected.length === 0 ? (
            <p className="mb0 muted">no known waste pattern found.</p>
          ) : (
            <div className="tags mt">
              {result.detected.map((d, i) => (
                <span key={i} className="tag" title={`${d.evidence} (line ${d.line})`}>
                  {d.waste_type} · L{d.line}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {result.proposer && (
        <div className="card mt">
          <div className="eyebrow">
            proposer {result.proposer.used ? `· ${result.proposer.provider}` : "· deterministic"}
          </div>
          <div className="row" style={{ alignItems: "flex-start" }}>
            <span className={`badge-free`} style={{ background: "var(--track)", color: "var(--ink-2)" }}>
              {result.proposer.used
                ? `LLM consulted${result.proposer.live ? " (live)" : ""}`
                : "deterministic detectors"}
            </span>
            <span className="muted" style={{ flex: 1 }}>{result.proposer.note}</span>
          </div>
          {result.proposer.rationale && (
            <pre
              className="mono"
              style={{
                whiteSpace: "pre-wrap",
                fontSize: 12,
                color: "var(--ink-2)",
                background: "var(--page)",
                border: "1px solid var(--line-soft)",
                borderRadius: 8,
                padding: "10px 12px",
                marginTop: 10,
              }}
            >
              {result.proposer.rationale}
            </pre>
          )}
          {result.proposer.detail && <div className="note warn mt">{result.proposer.detail}</div>}
        </div>
      )}

      {result.shipped.length > 0 && (
        <div className="mt">
          <div className="eyebrow"><Check /> shipped — each a floating object; the fill never crosses its ceiling</div>
          <div className="slab-stack">
            {result.shipped.map((s, i) => (
              <SpeedupSlab key={i} row={s} mode={result.mode} />
            ))}
          </div>
        </div>
      )}

      {result.declined.length > 0 && (
        <div className="card">
          <div className="eyebrow">declined — honest no-claims</div>
          {result.declined.map((d, i) => (
            <DeclinedVRow key={i} row={d} />
          ))}
        </div>
      )}

      {nothing && (
        <div className="card mt">
          <div className="row" style={{ alignItems: "flex-start" }}>
            <span className="ic" style={{ color: "var(--accent-deep)" }}><Info /></span>
            <p className="mb0">
              Nothing safe to ship. That's a real answer, not a failure — the engine only recognizes waste
              classes it has a verified fix for. {result.note}
            </p>
          </div>
        </div>
      )}

      <div className="honesty">
        <span className="ic"><Info /></span>
        <span>{result.note}</span>
      </div>

      <div className="row mt">
        <button className="ghost" onClick={onAgain}>
          ← Run another
        </button>
        <button className="btn" onClick={onCorpus}>
          See it on real repos <Arrow />
        </button>
      </div>
    </div>
  );
}
