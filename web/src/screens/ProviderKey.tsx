import { useState } from "react";
import type { KeyValidation, Provider } from "../types";
import { api } from "../api";
import { Arrow, Check, Lock } from "../icons";

export function ProviderKey({
  providers,
  picked,
  apiKey,
  onPick,
  onKey,
  onNext,
}: {
  providers: Provider[];
  picked: string | null;
  apiKey: string;
  onPick: (id: string) => void;
  onKey: (k: string) => void;
  onNext: () => void;
}) {
  const [checking, setChecking] = useState(false);
  const [result, setResult] = useState<KeyValidation | null>(null);
  const sel = providers.find((p) => p.id === picked) || null;

  async function check() {
    if (!picked || !apiKey) return;
    setChecking(true);
    setResult(null);
    try {
      setResult(await api.validateKey(picked, apiKey));
    } catch (e) {
      setResult({ ok: false, detail: String(e) });
    } finally {
      setChecking(false);
    }
  }

  return (
    <div className="fade">
      <div className="eyebrow">step 2 · proposer (optional)</div>
      <h2>Bring your own model, or skip.</h2>
      <p className="lead">
        The LLM only <em>proposes</em> rewrites — it never decides what ships; the verifier does. You can
        run the engine's verified detectors without any key at all. If you want LLM-proposed fixes, pick a
        provider and paste a key.
      </p>

      <div className="grid cols-2 mt">
        {providers.map((p) => (
          <button
            key={p.id}
            type="button"
            className="mode-card"
            aria-pressed={picked === p.id}
            onClick={() => {
              onPick(p.id);
              setResult(null);
            }}
            style={{ flexDirection: "row", alignItems: "center", gap: 12 }}
          >
            <span className="glyph" style={{ background: "var(--accent-tint)" }}>
              <Lock />
            </span>
            <div>
              <div className="mc-name" style={{ fontSize: 15, textTransform: "none" }}>{p.label}</div>
              <div className="mc-clock">
                {p.transport} · key env <span className="kbd">{p.key_env}</span>
              </div>
            </div>
          </button>
        ))}
      </div>

      {sel && (
        <div className="card mt fade">
          <div className="field">
            <label htmlFor="key">
              {sel.label} API key <span className="muted">(held in this tab only)</span>
            </label>
            <input
              id="key"
              type="password"
              autoComplete="off"
              spellCheck={false}
              placeholder={`paste your ${sel.label} key…`}
              value={apiKey}
              onChange={(e) => {
                onKey(e.target.value);
                setResult(null);
              }}
            />
          </div>
          <div className="row">
            <button className="ghost" onClick={check} disabled={!apiKey || checking}>
              {checking ? <span className="spin" /> : <Check />} Validate request shape
            </button>
            {result && (
              <span className={`note ${result.key_in_headers_only ? "good" : result.ok ? "" : "warn"}`}>
                {result.ok ? (
                  <>
                    {result.transport} → {result.url} ·{" "}
                    {result.key_in_headers_only ? "key in headers only ✓" : "checked"} · {result.detail}
                  </>
                ) : (
                  result.detail
                )}
              </span>
            )}
          </div>
          <div className="honesty">
            <span className="ic"><Lock /></span>
            <span>
              The key is sent once to build the request and confirm its shape; it is never logged, never
              written to disk, never committed, and only ever travels to {sel.label}'s own API. Live
              round-trip validation is <strong>UNVERIFIED</strong> in this sandbox (no outbound provider call).
            </span>
          </div>
        </div>
      )}

      <div className="row mt">
        <button className="btn" onClick={onNext}>
          {picked && apiKey ? "Continue to your code" : "Skip — run verified detectors only"} <Arrow />
        </button>
      </div>
    </div>
  );
}
