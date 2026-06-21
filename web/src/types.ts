// Types mirror exactly what the REAL pillar3 engine returns through webapi/engine_bridge.py.
// Nothing here is invented; each field is produced by a measured whole-program run.

export type ModeId = "fast" | "normal" | "extend";
export type Grade = "exact" | "probabilistic" | "decline";

export interface ModeContract {
  mode: ModeId;
  primary_clock: string;
  verifier_tier: string; // MICRO | CHEAP_CERT | FULL_CERT
  detectors: number;
  acceptable_grades: string[];
  max_hotspots: number | null;
  runs_complexity_sweep: boolean;
  latency_budget_s: number | null;
  risk_posture: string;
  stop_condition: string;
}

export interface Provider {
  id: string;
  label: string;
  transport: string; // anthropic_sdk | openai_chat | gemini_generate
  key_env: string;
}

export interface ShippedRow {
  name: string;
  waste_type: string;
  grade: Grade;
  ratio: number;
  ceiling: number | null; // null == unbounded (∞)
  hotspot_fraction: number;
}

export interface DeclinedRow {
  name: string;
  waste_type: string;
  reason: string;
}

export interface Detected {
  waste_type: string;
  evidence: string;
  line: number;
}

export interface OptimizeResult {
  mode: ModeId;
  detected: Detected[];
  shipped: ShippedRow[];
  declined: DeclinedRow[];
  cumulative_ratio: number;
  z3_calls: number;
  ran_complexity_sweep: boolean;
  latency_ms?: number;
  note: string;
  policy: ModeContract;
}

export interface KeyValidation {
  ok: boolean;
  live?: boolean;
  transport?: string;
  url?: string;
  key_in_headers_only?: boolean;
  detail: string;
}

export interface CorpusRow {
  name: string;
  archetype: string;
  detected: string[];
  grade: Grade;
  ratio: number;
  ceiling: number;
  hotspot_fraction: number;
  note: string;
}

export interface CorpusResult {
  rows: CorpusRow[];
  grades: { exact: number; probabilistic: number; decline: number };
  found_nothing: boolean;
}

export interface DemoRun {
  mode: ModeId;
  shipped: ShippedRow[];
  declined: DeclinedRow[];
  cumulative_ratio: number;
  z3_calls: number;
  latency_ms: number;
  ran_complexity_sweep: boolean;
}

export interface PanelRow {
  name: string;
  archetype: string;
  detected: string[];
  grade: Grade;
  ratio: number;
  ceiling: number;
  hotspot_fraction: number;
  note: string;
}

export interface Demo {
  engine: string;
  generated_by: string;
  modes: ModeContract[];
  providers: { id: string; label: string; transport: string }[];
  runs: DemoRun[];
  panel_rows: PanelRow[];
  key_policy?: string;
  scope_note?: string;
}
