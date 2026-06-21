import { useState } from "react";
import type { ModeId, OptimizeResult } from "../types";
import { api } from "../api";
import { SAMPLES } from "../samples";
import { Arrow, Info } from "../icons";

export function CodeRun({
  mode,
  provider,
  apiKey,
  model,
  code,
  onCode,
  onResult,
}: {
  mode: ModeId;
  provider: string | null;
  apiKey: string;
  model: string;
  code: string;
  onCode: (c: string) => void;
  onResult: (r: OptimizeResult) => void;
}) {
  const [running, setRunning] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function run() {
    if (!code.trim()) return;
    setRunning(true);
    setErr(null);
    try {
      const r = await api.optimize(
        code,
        mode,
        provider ?? undefined,
        apiKey || undefined,
        model || undefined
      );
      onResult(r); // parent advances to the verification panel
    } catch (e) {
      setErr(String(e));
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="fade" data-mode={mode}>
      <div className="eyebrow">step 3 · your code</div>
      <h2>Paste a function. We'll profile it for real.</h2>
      <p className="lead">
        Detection is genuine AST analysis of <em>your</em> source — your code is never executed. For each
        waste class we recognize, the engine runs its verified fix on a representative workload and reports
        the measured whole-program result under the <strong>{mode}</strong> contract.
      </p>

      <div className="samples mt mb0" style={{ marginBottom: 10 }}>
        <span className="muted" style={{ alignSelf: "center", fontSize: 12 }}>try:</span>
        {SAMPLES.map((s) => (
          <button key={s.label} onClick={() => onCode(s.code)}>
            {s.label}
          </button>
        ))}
        <label className="upload">
          upload .py ↑
          <input
            type="file"
            accept=".py,.txt,text/x-python,text/plain"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (!f) return;
              const r = new FileReader();
              r.onload = () => onCode(String(r.result || ""));
              r.readAsText(f);
              e.currentTarget.value = ""; // allow re-uploading the same file
            }}
          />
        </label>
      </div>

      <textarea
        className="editor"
        spellCheck={false}
        placeholder="def my_function(...):\n    ..."
        value={code}
        onChange={(e) => onCode(e.target.value)}
      />

      <div className="row mt">
        <button className="btn lg" onClick={run} disabled={running || !code.trim()}>
          {running ? <span className="spin" /> : null} Run {mode} verification <Arrow />
        </button>
        {provider ? (
          <span className="pill">proposer: {provider}</span>
        ) : (
          <span className="pill">verified detectors only (no LLM)</span>
        )}
        {err && <span className="note warn">{err}</span>}
      </div>

      <div className="honesty">
        <span className="ic"><Info /></span>
        <span>
          Auto-rewriting your exact source needs the LLM proposer plus a key — and even then the verifier
          arbitrates every swap. What you'll see next is the engine's verified result for each waste class
          it detected in your code.
        </span>
      </div>
    </div>
  );
}
