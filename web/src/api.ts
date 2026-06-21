// Typed client for the MR.JEFFREY back end. Relative /api paths work in dev (Vite proxy → :8000) and in
// prod (served same-origin from /app by FastAPI). The provider key is passed straight through to the
// back end's /api/key/validate and NEVER persisted, never put in a URL, never logged on this side.
import type {
  CorpusResult,
  Demo,
  KeyValidation,
  ModeContract,
  ModeId,
  OptimizeResult,
  Provider,
} from "./types";

async function jget<T>(path: string): Promise<T> {
  const r = await fetch(path, { headers: { accept: "application/json" } });
  if (!r.ok) throw new Error(`${path} → ${r.status}`);
  return (await r.json()) as T;
}

async function jpost<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(path, {
    method: "POST",
    headers: { "content-type": "application/json", accept: "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${path} → ${r.status}`);
  return (await r.json()) as T;
}

export const api = {
  health: () => jget<{ ok: boolean; engine: string; real: boolean }>("/api/health"),
  modes: () => jget<{ modes: ModeContract[] }>("/api/modes").then((d) => d.modes),
  providers: () => jget<{ providers: Provider[] }>("/api/providers").then((d) => d.providers),
  corpus: () => jget<CorpusResult>("/api/corpus"),
  demo: () => jget<Demo>("/api/demo"),
  // key (optional) is sent so the back end can call the proposer; it is never logged or stored server-side.
  optimize: (code: string, mode: ModeId, provider?: string, key?: string, model?: string) =>
    jpost<OptimizeResult>("/api/optimize", { code, mode, provider, key, model }),
  // key is sent only here, only for a live 1-token test call; the back end never logs/stores it.
  validateKey: (provider: string, key: string, model?: string) =>
    jpost<KeyValidation>("/api/key/validate", { provider, key, model }),
};

export type { ModeId };
