import { useState } from "react";
import type { KeyValidation, Provider } from "../types";
import { api } from "../api";
import { Arrow, Check, Info, Lock } from "../icons";
import { useTilt } from "../useTilt";

type VState = { phase: "idle" | "checking" | "ok" | "bad"; res?: KeyValidation };

// a provider as a neutral dimensional object (slate depth — never a mode accent, so it can't read as a mode)
function ProviderTile({ p, picked, onPick }: { p: Provider; picked: boolean; onPick: () => void }) {
  const ref = useTilt<HTMLButtonElement>(5);
  return (
    <button
      ref={ref}
      type="button"
      className="mode-card provider-card mode-slab"
      aria-pressed={picked}
      onClick={onPick}
      style={{ gap: 8 }}
    >
      <div className="mc-head" style={{ width: "100%" }}>
        <span className="glyph"><Lock /></span>
        <div style={{ flex: 1 }}>
          <div className="mc-name" style={{ fontSize: 15, textTransform: "none" }}>{p.label}</div>
          <div className="mc-clock">{p.transport}</div>
        </div>
        {p.free_no_card && <span className="badge-free"><span className="gd" />Free · no card</span>}
      </div>
      <div className="row" style={{ width: "100%", justifyContent: "space-between" }}>
        <span className="v-sub">default: <span className="mono">{p.default_model || "—"}</span></span>
        {p.get_key_url && (
          <a className="getkey" href={p.get_key_url} target="_blank" rel="noreferrer"
             onClick={(e) => e.stopPropagation()}>
            Get a key ↗
          </a>
        )}
      </div>
    </button>
  );
}

export function ProviderKey({
  providers,
  picked,
  apiKey,
  model,
  onPick,
  onKey,
  onModel,
  onValidated,
  onNext,
  onSkip,
}: {
  providers: Provider[];
  picked: string | null;
  apiKey: string;
  model: string;
  onPick: (p: Provider) => void;
  onKey: (k: string) => void;
  onModel: (m: string) => void;
  onValidated: (ok: boolean) => void;
  onNext: () => void;
  onSkip: () => void;
}) {
  const [v, setV] = useState<VState>({ phase: "idle" });
  const sel = providers.find((p) => p.id === picked) || null;

  function reset() {
    setV({ phase: "idle" });
    onValidated(false);
  }

  async function verify() {
    if (!picked || !apiKey) return;
    setV({ phase: "checking" });
    onValidated(false);
    try {
      const res = await api.validateKey(picked, apiKey, model || undefined);
      setV({ phase: res.ok ? "ok" : "bad", res });
      onValidated(res.ok);
    } catch (e) {
      setV({ phase: "bad", res: { ok: false, detail: String(e) } });
      onValidated(false);
    }
  }

  return (
    <div className="fade">
      <div className="eyebrow">step 2 · proposer · paste a free key and run</div>
      <h2>Pick a provider, paste a key — it just works.</h2>
      <p className="lead">
        The LLM only <em>proposes</em> rewrites; the verifier decides what ships. Groq and Gemini are free with
        no credit card, so they're the easiest way to test the whole site. You can also skip this and run the
        engine's verified detectors with no key at all.
      </p>

      <div className="grid cols-2 mt stage">
        {providers.map((p) => (
          <ProviderTile
            key={p.id}
            p={p}
            picked={picked === p.id}
            onPick={() => {
              onPick(p);
              reset();
            }}
          />
        ))}
      </div>

      {sel && (
        <div className="card mt fade">
          <div className="row" style={{ gap: 18, alignItems: "flex-start" }}>
            <div className="field" style={{ flex: 2, minWidth: 240, margin: 0 }}>
              <label htmlFor="key">
                {sel.key_label} {sel.free_no_card && <span className="badge-free"><span className="gd" />free</span>}
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
                  reset();
                }}
                onBlur={() => apiKey && verify()}
              />
            </div>
            <div className="field" style={{ flex: 1, minWidth: 180, margin: 0 }}>
              <label htmlFor="model">model</label>
              <input
                id="model"
                spellCheck={false}
                placeholder={sel.default_model}
                value={model}
                onChange={(e) => {
                  onModel(e.target.value);
                  reset();
                }}
              />
            </div>
          </div>

          <div className="row mt">
            <button className="ghost" onClick={verify} disabled={!apiKey || v.phase === "checking"}>
              {v.phase === "checking" ? <span className="spin" /> : <Check />} Verify key
            </button>
            {v.phase === "checking" && <span className="note">checking with {sel.label}…</span>}
            {v.phase === "ok" && <span className="note good"><Check /> valid — live {sel.label} call returned 200.</span>}
            {v.phase === "bad" && v.res && (
              <span className="note warn">
                {v.res.blocked ? "⚠ " : "✕ "}
                {v.res.detail}
                {!v.res.blocked && sel.get_key_url && (
                  <>
                    {" "}
                    <a className="getkey" href={sel.get_key_url} target="_blank" rel="noreferrer">Get a key ↗</a>
                  </>
                )}
              </span>
            )}
          </div>

          <div className="honesty">
            <span className="ic"><Lock /></span>
            <span>
              Your key stays in this session and is never stored, written to disk, logged, or committed — it only
              ever travels to {sel.label}'s own API. Verification makes a real 1-token test call.
              {sel.id === "groq" && " (In this sandbox api.groq.com is egress-blocked; Gemini validates live.)"}
            </span>
          </div>
        </div>
      )}

      <div className="row mt">
        <button className="btn" onClick={onNext} disabled={v.phase !== "ok"}>
          Continue to your code <Arrow />
        </button>
        <button className="ghost" onClick={onSkip}>
          Skip — run verified detectors only
        </button>
        {sel && v.phase !== "ok" && (
          <span className="note"><Info /> validate a key to continue, or skip to run without an LLM.</span>
        )}
      </div>
    </div>
  );
}
