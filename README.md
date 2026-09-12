# Manufacturing Inventory & Procurement Chat Agent

A conversational agent over a manufacturing company's Postgres DB (inventory + procurement), for 3 personas: inventory manager, procurement manager, owner. Decides per-query whether to answer in text, a table, or a chart. Bonus: gated DB write-back, existing auth reused (not rebuilt).

**Status / what's done vs pending:** see `tracker.md` - updated after every verified run, so it's the real state even if chat history gets overwritten.

**Why things were built the way they were:** see `info.md` - assumptions, alternatives considered, and rationale, logged phase by phase.

## Folder structure

Tags: ✅ built and verified · 🔄 built, verification in progress · ⬜ not started

```
manufacturing-agent/
├── README.md                 ✅ this file
├── info.md                   ✅ decisions + rationale log
├── tracker.md                ✅ completion tracker
├── .gitignore                ✅
├── scripts/
│   ├── dump_schema.py        ✅ one-off: dump real DB schema (Phase 1)
│   └── test_queries.py       ✅ automated test matrix + regression checks (Phase 5)
├── backend/                  ✅ Phase 2-3 - FastAPI + LangGraph agent (flat layout: files live directly in backend/)
│   ├── main.py                   FastAPI app: /chat, /confirm-write, /health
│   ├── db.py                     connection pool + schema introspection
│   ├── tools.py                  run_sql_read, propose_write, RespondToUser
│   ├── agent.py                  LangGraph graph + Postgres checkpointing
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
└── frontend/                  ✅ Phase 4 - Next.js chat UI
    ├── app/
    │   ├── layout.tsx             root layout + font imports (IBM Plex Sans/Mono)
    │   ├── page.tsx               main chat UI - personas, avatars, suggestions
    │   └── globals.css            design tokens (color/type/animation)
    ├── components/
    │   ├── TableRenderer.tsx
    │   ├── ChartRenderer.tsx      (Recharts - bar/line/pie)
    │   └── ConfirmWrite.tsx       write-back confirmation card
    ├── lib/api.ts                 backend fetch wrapper
    └── package.json
```

Each phase's tag flips ⬜ → 🔄 → ✅ here alongside `tracker.md`, right after
a run is actually verified - not before.

## Quick start

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

## Git workflow

One commit per verified working step. Branch per phase, merge into `main` once that phase's tracker items are ✅.

```bash
git add -A
git commit -m "phaseN: what changed - how it was verified"
```

Recent examples from this project:
```
phase2: fix response_type prompt - table/chart populate correctly, verified via 4 real queries phase2: fix dangling tool_call bug - verified via 5 real multi-turn queries (3 owner, 2 procurement) phase4: Next.js frontend - verified end-to-end against live backend
```

Branches so far: `phase2-backend-verified`, `phase4-frontend-verified` - merge each into `main` once its phase is fully ✅ in `tracker.md`.

## Status

Core loop (text/table/chart routing, multi-turn conversation, write-back proposal) is built and verified. **Deploy is required, not optional** - see `tracker.md` Phase 6 - gated on a full Phase 5 test pass first (the duplicate-row bug in particular needs a fix + re-verify before shipping).