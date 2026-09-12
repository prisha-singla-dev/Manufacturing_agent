# Tracker — Manufacturing Chat Agent

Legend: ✅ done · 🔄 in progress · ⬜ not started · ⏭️ skipped (stretch, out of budget)

## Phase 0 — Planning
- ✅ Use case captured, feasibility confirmed
- ✅ Assumptions documented (info.md)
- ✅ Phase plan agreed
- ✅ info.md created
- ✅ tracker.md created
- ✅ Real schema provided (27 tables — more than expected, includes LangGraph + auth infra already set up)

## Phase 1 — Test cases + schema
- ✅ 11 draft test cases across all 3 personas (in info.md phase log)
- ✅ Schema confirmed real; scoped agent's view to 16 business tables, excluding LangGraph/auth internals
- ✅ Persona → role mapping confirmed (owner / procurement_manager / inventory_manager, via users table)
- ⬜ Mark which test cases expect text / table / chart (drafted, not all verified against real answers yet)
- ⬜ Mark which test cases expect a write-back
- ⬜ Additional seed data if any test case needs more demo-worthy numbers

## Phase 2 — Backend skeleton
- ✅ FastAPI app scaffolded (`/chat`, `/confirm-write`, `/health`)
- ✅ LangGraph agent graph defined (read loop + structured RespondToUser terminal tool)
- ✅ SQL read tool — **verified working**: curl to `/chat` returned a correct, DB-grounded answer (min-stock query)
- ✅ Reuses existing `checkpoints`/`checkpoint_writes` tables for persistence (no new setup needed)
- ⬜ LangSmith tracing confirmed showing up in the LangSmith UI (code wired, not yet visually confirmed)
- ⬜ Write-back tool (`propose_write` + `/confirm-write`) tested end-to-end
- ⬜ Chart/table response types verified (only a text-type response tested so far)

## Phase 3 — Response typing + write-back tool
- ⬜ Structured response schema (`response_type`, `chart_type`, `data`, `text`)
- ⬜ Visualization-decision logic tested against ambiguous cases
- ⬜ Write-back tool (propose → confirm → execute) — BONUS
- ⬜ Guardrail: write tool cannot execute without explicit confirm flag

## Phase 4 — Frontend
- ⬜ Next.js chat UI (message list, input, persona switcher)
- ⬜ Table renderer
- ⬜ Chart renderer (Recharts)
- ⬜ Write-back confirmation UI

## Phase 5 — Integration + test-case pass
- ⬜ All Phase 1 test cases run end-to-end
- ⬜ Failures triaged via LangSmith traces
- ⬜ Fixes applied and re-tested

## Phase 6 — Stretch
- ⬜ Authentication — BONUS, not mandatory
- ⬜ Cloud deploy: backend (Railway/Render)
- ⬜ Cloud deploy: frontend (Vercel)

---
## Decisions log (running, most recent first)
- 2026-09-12 — No Claude Code available; workflow adapted to: Claude generates
  code in this chat → user runs locally (has real DB/network access) → pastes
  back output/errors → iterate. Git commit after each verified step.
- 2026-09-12 — First working `/chat` call verified end-to-end against the
  real DB (inventory_manager persona, min-stock query, correct answer).
- 2026-09-12 — Real schema turned out to be 27 tables, not 17: includes
  LangGraph's own checkpoint tables (already in use — 888+ existing rows) and
  a working auth system (`users`, `refresh_tokens`). Agent's schema view
  scoped to the 16 real business tables only.
- 2026-09-12 — Planning phase closed; sandbox lacks DB/deploy network access, so
  build/run/deploy work recommended to happen via Claude Code, not this chat.