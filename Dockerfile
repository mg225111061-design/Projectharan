# HARAN web — one image: Python engine (Z3 / sympy) + FastAPI + v22 agentic pipeline + front-end.
# Local-only by default (you, now, free). The SAME image deploys later (Cloud Run / Render) with zero
# code change — only env vars differ. See HARAN_v23_README.md.
FROM python:3.11-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app

# Optional: Coq enables unbounded-∀ proofs (extended mode, hard cases). It is HEAVY, so it's OFF by
# default to keep the image lean — without it those cases honestly DEFER (UNRESOLVED), never wrong.
# Enable with:  docker build --build-arg INSTALL_COQ=true .
ARG INSTALL_COQ=false
RUN if [ "$INSTALL_COQ" = "true" ]; then \
        apt-get update && apt-get install -y --no-install-recommends coq && \
        rm -rf /var/lib/apt/lists/* ; \
    fi

COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

# Config via env (NOT hardcoded). ★ The Claude API key is NEVER an env var or baked into the image —
#   it is entered per request in the browser, used once for the call, and dropped (level-1). ★
# NOTE: HARAN_PORT is left UNSET so the app binds Render/Cloud-Run's injected $PORT (server.py honors
#   HARAN_PORT → PORT → 8000). Set HARAN_PORT only for a fixed local port.
ENV HARAN_HOST=0.0.0.0
EXPOSE 8000 10000

# Launch the REAL backend: uvicorn serving `server:app` — the ONE process that serves BOTH the Korean
# single-file UI at `/` (mrjeffrey.html, everything inlined) AND the live engine at `/api/*`
# (math/solve · math/ingest · optimize · key/validate · health). The frontend's fetch('/api/math/solve')
# reaches THIS process, so MATH actually proves/computes (fold · arsenal · broth) instead of the static
# fallback. Binds Render's injected $PORT (defaults to 10000 locally). This is equivalent to `python server.py`
# (which calls uvicorn.run with host 0.0.0.0, port $PORT) but states the entrypoint explicitly.
# ── IMPORTANT: this image is a WEB SERVICE (it runs Python). A Render *Static Site* CANNOT run it and will
#    serve only files — then /api/* is unreachable and MATH shows "정적 빌드 / 라이브 엔진 없음". See DEPLOY_NOTES.md. ──
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-10000}"]
