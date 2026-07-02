# SEARCH_INDEX — search toggle pre-build index (PART 2 §T1)

`grep`/`view` index of the existing search/web surface before adding the ON/OFF toggle.

## Finding: there is NO web/search tool exposed to the LLM today
- `grep -i "web_search|websearch|search_tool|tool_use|tools=|tavily|serp|brave_search|duckduckgo"` over the repo
  matched **only documentation** (`reports/archive/*CITATIONS*.md`) — never a live search-tool call site.
- The LLM call paths (`claude_agent.claude_generate` SDK path; `webapi/engine_bridge._provider_request` raw HTTP)
  send a single prompt and read back text. **No tool-use / function-calling loop, no search tool, is wired.**
- So "search" is currently 0 by construction. The toggle's job is to make that an *explicit, user-controlled*
  state and to provide the **structural gate** for when a search tool is added.

## Frontend state pattern (where the toggle lives)
- React app `web/src/` uses `useState` (App.tsx, CodeRun.tsx, ProviderKey.tsx, Corpus.tsx) and a small `api` client.
  State is held in React, NOT raw `localStorage` (follow the existing pattern — lift state in `App.tsx`, pass props).
- `mrjeffrey.html` is the single-file conversational entry (text-first, intent-routed) served at `/`.

## Design (honest, given no search backend + egress-blocked sandbox)
1. **Backend gate (the real guarantee, testable):** a `search_allowed: bool` flag travels with the request.
   - **OFF** → the search tool is **not placed in the tool list** handed to the LLM → calling it is impossible →
     **search count = 0** (a structural guarantee, not a prompt request).
   - **ON** → the tool *would be* exposed, BUT the system prompt instructs "search only when needed (fresh/unknown
     facts); for things you know or static reasoning, just answer" → ON ≠ search-every-time (LLM-judged).
   - Implemented as a pure, tested policy (`search_gate.py`): `tools_for(search_allowed)` returns `[]` when OFF and
     the (future) search tool spec when ON; `system_suffix(search_allowed)` adds the "only when needed" guidance.
2. **Frontend toggle:** an ON/OFF control in the conversational UI showing "검색: 켜짐/꺼짐"; when ON, the
   sub-note "필요할 때만 검색합니다". State lifted in the app and sent on each request as `searchAllowed`.
3. **Honesty:** no real search provider is wired yet and this sandbox egress-blocks the open web — so an actual
   search EXECUTION is out of scope here; the deliverable is the **gate + toggle + prompt policy** (the contract
   that OFF=0 and ON=available-but-judged), which the author can connect to a real search backend on Render.
4. **Security (PART 1 applies):** if/when search hits the network, it rides the same egress + input-validation +
   no-key-leak rules as the provider path.
