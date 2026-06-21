import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import type { Demo, ModeContract, ModeId, OptimizeResult, Provider } from "./types";
import { Landing } from "./screens/Landing";
import { ModeSelect } from "./screens/ModeSelect";
import { ProviderKey } from "./screens/ProviderKey";
import { CodeRun } from "./screens/CodeRun";
import { Verification } from "./screens/Verification";
import { Corpus } from "./screens/Corpus";
import { Toast } from "./components/Toast";

type Screen = "landing" | "mode" | "provider" | "code" | "verify" | "corpus";

const STEPS: { id: Screen; n: string; label: string }[] = [
  { id: "landing", n: "0", label: "Overview" },
  { id: "mode", n: "1", label: "Mode" },
  { id: "provider", n: "2", label: "Provider" },
  { id: "code", n: "3", label: "Code" },
  { id: "verify", n: "4", label: "Verify" },
  { id: "corpus", n: "5", label: "Proof" },
];

export default function App() {
  const [screen, setScreen] = useState<Screen>("landing");
  // initial theme follows the OS — the white volume inverts to a deep near-black volume automatically
  const [theme, setTheme] = useState<"light" | "dark">(() =>
    typeof window !== "undefined" && window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light"
  );

  const [modes, setModes] = useState<ModeContract[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [demo, setDemo] = useState<Demo | null>(null);
  const [bootErr, setBootErr] = useState<string | null>(null);

  // session — the key lives ONLY here, in tab memory. Never localStorage, never logged.
  const [mode, setMode] = useState<ModeId | null>(null);
  const [provider, setProvider] = useState<string | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("");
  const [keyValid, setKeyValid] = useState(false);
  const [code, setCode] = useState("");
  const [result, setResult] = useState<OptimizeResult | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  useEffect(() => {
    Promise.all([api.modes(), api.providers(), api.demo()])
      .then(([m, p, d]) => {
        setModes(m);
        setProviders(p);
        setDemo(d);
      })
      .catch((e) => setBootErr(String(e)));
  }, []);

  const activeMode: ModeId = mode ?? "extend";
  const reached = useMemo(() => {
    // which steps are navigable given session progress
    const r: Record<Screen, boolean> = {
      landing: true,
      mode: true,
      provider: !!mode,
      code: !!mode,
      verify: !!result,
      corpus: true,
    };
    return r;
  }, [mode, result]);

  function restart() {
    setMode(null);
    setProvider(null);
    setApiKey("");
    setModel("");
    setKeyValid(false);
    setCode("");
    setResult(null);
    setScreen("landing");
  }

  return (
    <div className="app" data-mode={activeMode}>
      <header className="topbar">
        <div className="brand">
          <span className="dot" />
          MR.JEFFREY <small>whole-program verified speedup</small>
          {!demo && !bootErr && <span className="syncing" aria-live="polite">· syncing engine…</span>}
        </div>
        <nav className="steps" aria-label="progress">
          {STEPS.map((s) => (
            <button
              key={s.id}
              aria-current={screen === s.id}
              disabled={!reached[s.id]}
              onClick={() => setScreen(s.id)}
            >
              <span className="n">{s.n}</span>
              {s.label}
            </button>
          ))}
        </nav>
        <div className="spacer" />
        <button
          className="ghost"
          onClick={() => setTheme((t) => (t === "light" ? "dark" : "light"))}
          aria-label="toggle theme"
        >
          {theme === "light" ? "Dark" : "Light"}
        </button>
      </header>

      <main className={screen === "corpus" || screen === "verify" ? "wide" : undefined}>
        {bootErr && (
          <div className="card">
            <strong>Back end unreachable.</strong>
            <p className="mb0">
              The API at <span className="kbd">/api</span> didn't respond ({bootErr}). Start it with{" "}
              <span className="kbd">uvicorn webapi.app:app --port 8000</span> (dev) — the Vite proxy
              forwards <span className="kbd">/api</span> there.
            </p>
          </div>
        )}

        {screen === "landing" && <Landing demo={demo} onStart={() => setScreen("mode")} />}

        {screen === "mode" && (
          <ModeSelect
            modes={modes}
            picked={mode}
            onPick={(m) => setMode(m)}
            onNext={() => setScreen("provider")}
          />
        )}

        {screen === "provider" && (
          <ProviderKey
            providers={providers}
            picked={provider}
            apiKey={apiKey}
            model={model}
            onPick={(p) => {
              setProvider(p.id);
              setModel(p.default_model);
              setKeyValid(false);
            }}
            onKey={setApiKey}
            onModel={setModel}
            onValidated={setKeyValid}
            onNext={() => setScreen("code")}
            onSkip={() => {
              setProvider(null);
              setApiKey("");
              setKeyValid(false);
              setScreen("code");
            }}
          />
        )}

        {screen === "code" && (
          <CodeRun
            mode={activeMode}
            provider={keyValid ? provider : null}
            apiKey={keyValid ? apiKey : ""}
            model={model}
            code={code}
            onCode={setCode}
            onResult={(r) => {
              setResult(r);
              setScreen("verify");
              const n = r.shipped.length;
              setToast(
                n > 0
                  ? `Optimization complete — ${n} verified fix${n === 1 ? "" : "es"} shipped`
                  : "Optimization complete — nothing safe to ship (honest DECLINE)"
              );
            }}
          />
        )}

        {screen === "verify" && result && (
          <Verification result={result} onAgain={() => setScreen("code")} onCorpus={() => setScreen("corpus")} />
        )}

        {screen === "corpus" && <Corpus onRestart={restart} />}
      </main>

      <footer className="footer">
        Measured whole-program · Amdahl-honest · grades enforced · proposer ≠ arbiter · keys held in-tab only.
      </footer>

      <Toast msg={toast} onDone={() => setToast(null)} />
    </div>
  );
}
