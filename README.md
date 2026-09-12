# Manufacturing Inventory & Procurement Chat Agent

A conversational agent over a manufacturing company's Postgres DB (inventory + procurement), for 3 personas: inventory manager, procurement manager, owner.
Decides per-query whether to answer in text, a table, or a chart. 

Bonus:
gated DB write-back, existing auth reused (not rebuilt).

**Status / what's done vs pending:** see `tracker.md` — that's the source of truth, kept up to date after every working run so nothing is lost if this chat history gets overwritten.

**Why things were built the way they were:** see `info.md` — assumptions, alternatives considered, and rationale, logged phase by phase.

## Folder structure

Tags: ✅ built and verified · 🔄 built, not yet verified · ⬜ not started

```
manufacturing-agent/
├── README.md                 ✅ this file
├── info.md                   ✅ decisions + rationale log
├── tracker.md                ✅ completion tracker
├── .gitignore                ✅
├── scripts/
│   └── dump_schema.py        ✅ one-off: dump real DB schema (Phase 1)
├── backend/                  🔄 Phase 2-3 — FastAPI + LangGraph agent
│   ├── main.py                   FastAPI app: /chat, /confirm-write, /health
│   ├── db.py                     connection pool + schema introspection
│   ├── tools.py                  run_sql_read, propose_write, RespondToUser
│   ├── agent.py                  LangGraph graph + Postgres checkpointing
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md                 backend-specific run instructions
└── frontend/                  ⬜ Phase 4 — Next.js chat UI (not yet added)
    ├── app/
    ├── components/
    │   ├── ChatWindow.tsx
    │   ├── TableRenderer.tsx
    │   ├── ChartRenderer.tsx
    │   └── PersonaSwitcher.tsx
    └── package.json
```

Each phase adds its folder/files to this tree as it's completed — this
README gets updated (tag flips ⬜ → 🔄 → ✅) alongside `tracker.md` right
after a run is verified, not before.

## Quick start (backend, currently the only runnable piece)

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # fill in real values
uvicorn main:app --reload --port 8000
```

See `backend/README.md` for test commands.

## Git workflow

One commit per verified working step — small, and each one tells you exactly
what state the code was in when it worked. Not one giant commit at the end.

```bash
git init                                 # once, at project root
git add -A
git commit -m "phase0: planning docs + schema dump script"
```

**Commit message convention:** `phaseN: what changed — how it was verified`

Examples matching what we've actually done so far:
```
phase1: confirm real DB schema (27 tables) + persona/role mapping via users table
phase2: backend skeleton (FastAPI + LangGraph agent, read-only SQL tool) — verified via curl /chat, correct min-stock answer
```

Going forward, commit right after each message in this chat where something
new gets verified working — that keeps `tracker.md` and the git history in
sync, so either one alone tells you the real state of the project.