# AGENTS.md

Instructions for coding agents (Antigravity, Gemini CLI and others) working in this repository.

## What this is

Trend Signals is a reference blueprint: an analytics workspace that runs in the Gemini Enterprise Canvas side panel,
with an ADK agent in the chat that analyzes the data and changes what the workspace shows. The workspace is a React
page built to one HTML file and delivered in an A2UI v0.9 `IFrameSrcdoc` inside a `Canvas`; the agent is an A2A
service on Cloud Run. The data is illustrative (a fictional retailer, Cymbal Apparel).

Read before changing anything:
1. `README.md`: what the blueprint demonstrates, quick start, constraints of the Gemini Enterprise frame.
2. `docs/HOW_IT_WORKS.md`: the design in depth (request flow, state contract, agent, page, time limits, testing).
3. `docs/ARCHITECTURE.md`: the short reference. `docs/THEMING.md`: the styling system.

## Skills

`.agents/skills.json` registers `skills/`:
- `ge-agentic-workspace`: building or adapting a workspace like this one. Start here for any change to the page,
  the tools or the state.
- `gemini-enterprise-a2ui`: A2UI v0.9 for Gemini Enterprise (components, messages, rendering behavior, validation,
  registration, API testing).

## Layout

| Path | Content |
|---|---|
| `src/trend_signals/catalog.py` | The illustrative dataset. Replace it with a data product; keep the shape. |
| `src/trend_signals/tools.py` | The agent's tools. Read tools return compact data; write tools change `ui_state`. |
| `src/trend_signals/ui_state.py`, `state.py`, `canvas.py` | Workspace state, the state injected into the page, the Canvas surface. |
| `src/trend_signals/executor.py`, `agent.py`, `prompts.py` | One A2A turn, the ADK agent, its instruction. |
| `src/trend_signals/kit/` | Generic Gemini Enterprise and A2UI plumbing, reusable in any agent. |
| `frontend/` | The workspace page (React, TypeScript, Tailwind v4, Radix, d3, Motion, Vite single-file build). |
| `deploy/`, `registration/` | Cloud Run deployment and Gemini Enterprise registration. |
| `scripts/` | `chat.py` (A2A, local or deployed), `ge_client.py` (through the Gemini Enterprise API), screenshots, smoke test. |
| `tests/` | Unit tests. |

## Commands

```bash
make install            # uv sync, npm ci
make check              # lint + tests (builds the page first); run before every commit
make gallery            # the page on :5173 with the illustrative data, no agent needed
make screenshots        # renders every view to docs/images/ (needs: uv run playwright install chromium)
make run                # local A2A server on :8080 (needs .env and Application Default Credentials)
uv run python scripts/chat.py "Where are my biggest whitespace gaps?"
make deploy             # Cloud Run, about 6 minutes
make register           # Gemini Enterprise; re-run after ANY change to the agent card (card.py)
```

## Rules

- **No project details in tracked files.** No project ids or numbers, app (engine) ids, service URLs, bucket names,
  emails or keys, not even as defaults. Configuration lives in `.env` (gitignored); `.env.example` holds placeholders.
  Scripts fail with a clear message when a setting is missing; they never fall back to a guessed value.
- **No silent fallbacks.** When something fails, fail loudly with the fix.
- **Validate surfaces.** Every A2UI surface is validated against the composite catalog
  (`src/trend_signals/kit/ge_composite_catalog_v0_9.json`); one A2UI message stays under 1 MiB.
- **The frame is fixed.** The page is an app shell in a fixed-height frame: pinned header, one scrolling content
  region. Do not turn it into a long page; the Canvas panel does not scroll.
- **The page is sealed.** No network calls, no links that navigate, no storage, no external images. All data is in
  the page; illustrations are SVG.
- **Theme through tokens.** Colors come from `frontend/src/lib/tokens.css`, in a light and a dark theme. Keep all CSS
  in Tailwind's layers.
- **Time limits.** Keep model calls within `MODEL_CALL_TIMEOUT_MS` and a turn within `TURN_TIMEOUT_S`; Gemini
  Enterprise drops slow agents.
- **One instance.** Workspace state is in memory, so the service runs with one instance. Move `ui_state` to a shared
  store (for example Firestore) before raising `MAX_INSTANCES`.
- Every source file starts with the Apache 2.0 header used in the existing files.
