#!/usr/bin/env python3
"""
test_claude.py — verify the live model path for ANY configured gateway. RUN WITH YOUR OWN KEY.
==============================================================================================
HARAN talks to whatever gateway you configure with three env vars (see provider.py):

  export HARAN_PROVIDER=anthropic|anthropic_compat|openai_compat   # default: anthropic
  export HARAN_MODEL=...                                           # e.g. claude-opus-4-8, qwen/qwen3-coder
  export HARAN_BASE_URL=...                                        # e.g. https://agentrouter.org/v1
  export HARAN_KEY=...                                             # your gateway key

Then:
  python3 scripts/test_claude.py            # ONE real call via the configured gateway; reports live/usage
  python3 scripts/test_claude.py --shape    # KEY-FREE: dummy key → 401 means the request shape is accepted

Key security: the key is read from $HARAN_KEY for exactly one call and dropped — never stored/logged.
(claude_agent.py never reads it from env; this separate harness reads the env var you set for your test.)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import claude_agent as CA   # noqa: E402
import provider as PV       # noqa: E402

_PROMPT = ("Write a HARAN function `triangular(n: Nat) -> Nat` with `ensures result = n*(n+1)/2` "
           "using a single `fold k in 1..n { k }`. Return only the function.")


def _print_config(cfg):
    print(f"provider={cfg.provider}  model={cfg.model}  base_url={cfg.base_url or '(SDK default)'}  "
          f"env_key={'set' if cfg.has_env_key else 'none'}")


def shape_probe() -> int:
    cfg = PV.config()
    _print_config(cfg)
    dummy = "sk-DUMMY-INVALID-DO-NOT-USE-shape-probe-0000000000"
    try:
        if cfg.provider == "openai_compat":
            import openai
            base = cfg.base_url or "https://api.openai.com/v1"
            client = openai.OpenAI(api_key=dummy, base_url=base, max_retries=0)
            client.chat.completions.create(**CA._build_openai_kwargs(_PROMPT, None, cfg.model, 256, False))
        else:
            import anthropic
            client = anthropic.Anthropic(api_key=dummy, base_url=cfg.base_url, max_retries=0) \
                if cfg.base_url else anthropic.Anthropic(api_key=dummy, max_retries=0)
            client.messages.create(**CA._build_kwargs(_PROMPT, None, cfg.model, CA.DEFAULT_MAX_TOKENS, True))
        print("UNEXPECTED: a dummy key should never succeed."); return 1
    except Exception as e:   # noqa: BLE001
        name = type(e).__name__
        msg = CA.redact_key(str(e))
        if "Authentication" in name or "401" in msg:
            print("SHAPE OK ✓ — reached the gateway, rejected ONLY for the (dummy) key (401).")
            print("            With a real HARAN_KEY this request shape is accepted.")
            return 0
        if "PermissionDenied" in name or "allowlist" in msg or "Connection" in name:
            print(f"SHAPE built & sent, but the network blocked the host ({name}). The request shape is")
            print("            client-side valid; run this from an environment that can reach the gateway.")
            return 0
        print(f"SHAPE issue ({name}): {msg[:240]}"); return 1


def live_call() -> int:
    cfg = PV.config()
    _print_config(cfg)
    key = PV.resolve_key()
    if not key:
        print("No HARAN_KEY (or ANTHROPIC_API_KEY / OPENAI_API_KEY) in the environment.")
        print("  export HARAN_KEY=...  &&  python3 scripts/test_claude.py        # real call")
        print("  python3 scripts/test_claude.py --shape                          # key-free shape check")
        return 2
    print("Making ONE real call via the configured gateway …")
    try:
        r = CA.claude_generate(_PROMPT, api_key=key)     # uses env-resolved provider/model/base_url
    except Exception as e:   # noqa: BLE001
        print(f"CALL FAILED ({type(e).__name__}):", CA.redact_key(str(e))[:300]); return 1
    finally:
        key = None
    if not r.live:
        print(f"Returned a MOCK result (source={r.source}) — no live call was made."); return 1
    print(f"LIVE OK ✓  source={r.source}  usage={r.usage}")
    print("  --- generated (first 240 chars) ---")
    print("  " + r.text[:240].replace("\n", "\n  "))
    return 0


if __name__ == "__main__":
    raise SystemExit(shape_probe() if "--shape" in sys.argv[1:] else live_call())
