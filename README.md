# Manufacturing Inventory & Procurement Chat Agent

A conversational agent over a manufacturing company's Postgres DB (inventory +
procurement), for 3 personas: inventory manager, procurement manager, owner.
Decides per-query whether to answer in text, a table, or a chart. Bonus:
gated DB write-back, existing auth reused (not rebuilt).

**Status / what's done vs pending:** see `tracker.md` — updated after every
verified run, so it's the real state even if chat history gets overwritten.

**Why things were built the way they were:** see `info.md` — assumptions,
alternatives considered, and rationale, logged phase by phase.

## Folder structure

Tags: ✅ built and verified · 🔄 in progress · ⬜ not started

```
manufacturing-agent/
├── README.md                 ✅ this file
├── info.md                   ✅ decisions + rationale log
├── tracker.md                ✅ completion tracker
├── .gitignore                ✅
├── scripts/
│   ├── dump_schema.py        ✅ one-off: dump real DB schema (Phase 1)
│   └── test_queries.py       ✅ automated test matrix + regression checks (Phase 5)
├── backend/                  ✅ Phase 2-3-5 — FastAPI + LangGraph agent
│   ├── main.py                   FastAPI app: /chat, /confirm-write, /health
│   ├── db.py                     connection pool + schema introspection
│   ├── tools.py                  run_sql_read, propose_write, RespondToUser
│   ├── agent.py                  LangGraph graph + Postgres checkpointing
│   ├── requirements.txt
│   ├── .env.example
│   ├── Procfile                  ✅ Phase 6 — Railway start command
│   └── README.md
└── frontend/                  ✅ Phase 4 — Next.js chat UI
    ├── app/
    │   ├── layout.tsx             root layout + font imports (IBM Plex Sans/Mono)
    │   ├── page.tsx               main chat UI — personas, avatars, suggestions
    │   └── globals.css            design tokens (color/type/animation)
    ├── components/
    │   ├── TableRenderer.tsx
    │   ├── ChartRenderer.tsx      (Recharts — bar/line/pie)
    │   └── ConfirmWrite.tsx       write-back confirmation card
    ├── lib/api.ts                 backend fetch wrapper
    └── package.json
```

Each phase's tag flips ⬜ → 🔄 → ✅ here alongside `tracker.md`, right after
a run is actually verified — not before.

## Quick start (local)

**Backend:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # fill in real values
uvicorn main:app --reload --port 8000
```

**Frontend** (backend must already be running):
```bash
cd frontend
npm install
copy .env.local.example .env.local
npm run dev
```
Open http://localhost:3000.

**Test everything at once:**
```bash
cd scripts
pip install requests
python test_queries.py
```

## Deploy

**Backend → Railway** (same project as the existing Postgres DB):
1. Push to GitHub, then Railway → New → GitHub Repo → set Root Directory to `backend`
2. Add env vars: `DATABASE_URL`, `OPENAI_API_KEY`, `LANGSMITH_API_KEY`,
   `LANGSMITH_TRACING=true`, `LANGSMITH_PROJECT`, `ALLOWED_ORIGINS`
3. Deploy — Railway uses the `Procfile` automatically. Copy the resulting URL.

**Frontend → Vercel:**
1. Vercel → New Project → import the same repo → set Root Directory to `frontend`
2. Add env var `NEXT_PUBLIC_API_URL` = the Railway URL from above
3. Deploy — copy the resulting URL

**Close the loop:** update Railway's `ALLOWED_ORIGINS` to include the Vercel
URL (comma-separated with localhost), which redeploys automatically. Without
this, the deployed frontend's requests are blocked by CORS.

## Git workflow

One commit per verified working step. Branch per phase, merge into `main`
once that phase's tracker items are ✅.

```bash
git add -A
git commit -m "phaseN: what changed — how it was verified"
```

Branches so far: `phase2-backend-verified`, `phase4-frontend-verified` — merge
each into `main` once its phase is fully ✅ in `tracker.md`.

## Live URLs

- **App:** https://manufacturing-agent-delta.vercel.app/
- **API:** https://manufacturingagent-production.up.railway.app/

## Status

**Fully built, tested, and deployed.** Text/table/chart routing, multi-turn
conversation, write-back (propose → confirm → execute) with guardrails
(WHERE-required UPDATE, no DELETE/DROP, raw SQL shown before confirming),
LangSmith tracing confirmed. Full 11-query test matrix plus a 9-case
adversarial suite (prompt injection, sensitive-data probes, guardrail-bypass
attempts) run against the live deployment — 0 automated safety issues.

Ten real bugs were found and fixed along the way against the actual
production database rather than a mock — see `info.md` for each one's root
cause and fix, and `tracker.md` for current status. One known cosmetic
edge case remains (an LLM non-determinism issue where one specific query
occasionally formats data as text instead of a table/chart — functionally
correct, just not always the ideal render) and is documented rather than
hidden.