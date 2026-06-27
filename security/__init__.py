"""
§R — CONDITIONAL VERIFIED SECURITY: the LLM decides whether security matters; the verifier proves whether the code is
secure. When the LLM gate says NOT-SENSITIVE the layer stays OFF (measured ~0 overhead); when it says SENSITIVE the
verified layer proves vulnerability-absence (logical by z3/QF_BV, side-channel by constant-time taint + masking) or
flags it honestly — "safe" only when proved, never a false assurance. Revives ct_certifier (anti-KyberSlash lineage)
and points it at general LLM-written code. Modules: llm_gate · logical_vulns · sidechannel · hardening ·
overhead_report · security_report. Zero external deps; never imported by test_build.
"""
