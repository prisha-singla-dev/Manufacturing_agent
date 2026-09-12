# Tracker — Manufacturing Chat Agent

Legend: ✅ done · 🔄 in progress · ⬜ not started · ⏭️ skipped

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
- ✅ Automated test runner built (`scripts/test_queries.py`) covering the full matrix with self-checks for both known bugs
- ⬜ Additional seed data if any test case needs more demo-worthy numbers

## Phase 2 — Backend skeleton
- ✅ FastAPI app scaffolded (`/chat`, `/confirm-write`, `/health`)
- ✅ LangGraph agent graph defined (read loop + structured RespondToUser terminal tool)
- ✅ SQL read tool — verified via curl (min-stock query, correct DB-grounded answer)
- ✅ Reuses existing `checkpoints`/`checkpoint_writes` tables for persistence
- ✅ Chart/table response-typing bug — found, fixed, verified across 4 real queries
- ✅ Multi-turn dangling-tool-call bug — found, fixed, **verified via 5 real multi-turn queries (3 owner, 2 procurement)**
- ⬜ LangSmith tracing confirmed visually in the LangSmith UI
- 🔄 Write-back tool (`propose_write` + `/confirm-write`) — code complete, test #11 in progress now
- ⬜ **Queued fix:** pending-POs table query returns duplicate/fan-out rows (join not aggregated) — inflates counts, mislabels PO-lines as POs. Now auto-detected by `test_queries.py`'s duplicate-id check.

## Phase 3 — Response typing + write-back tool
- ✅ Structured response schema (`response_type`, `chart_type`, `data`, `text`) — implemented and verified
- ✅ Visualization-decision logic tested against real ambiguous cases (single number vs list vs trend)
- 🔄 Write-back tool (propose → confirm → execute) — BONUS — code complete, end-to-end test in progress
- ✅ Guardrail confirmed by design: write tool cannot execute without a separate `/confirm-write` call

## Phase 4 — Frontend
- ✅ Next.js chat UI (persona switcher, message list, input)
- ✅ Table renderer
- ✅ Chart renderer (Recharts — bar/line/pie)
- ✅ Write-back confirmation UI
- ✅ Verified running against the live backend — multi-turn, both bugs' fixes confirmed
- ✅ **UI redesign** — industrial token palette (IBM Plex Sans/Mono, steel/slate/ink), avatars, timestamps, animated typing indicator, clickable suggested-question chips. User-confirmed: "rendering is perfect."

## Phase 5 — Integration + full test-case pass (current focus — required before deploy)
- 🔄 Automated test runner built; awaiting a full run + review of flagged anomalies
- ⬜ Test #11 (write-back) completed end-to-end, including actual `/confirm-write` execution
- ⬜ Duplicate-row bug (pending POs) fixed and re-verified
- ⬜ LangSmith traces reviewed for any silent failures the response-level checks wouldn't catch
- ⬜ All 11 test-matrix queries clean (no anomalies flagged)

## Phase 6 — Deploy (not a stretch — required; gated on Phase 5 passing)
- ⬜ Authentication — BONUS, still optional
- ⬜ Cloud deploy: backend (Railway or Render)
- ⬜ Cloud deploy: frontend (Vercel)
- ⬜ End-to-end smoke test against the deployed URLs (not just localhost)

---
## Decisions log (running, most recent first)
- 2026-09-12 — Deploy reclassified from "stretch" to required, gated on a full
  Phase 5 test pass. Built `scripts/test_queries.py` to test the whole matrix
  automatically instead of one manual curl at a time, with built-in checks
  for both bugs already found (markdown-in-text, duplicate rows by id).
- 2026-09-12 — Frontend UI redesigned per user feedback ("too basic") —
  industrial-toned design system (IBM Plex Sans/Mono, steel/slate/ink
  palette) matching the subject matter, avatars + timestamps + typing
  indicator + suggested-question chips. User confirmed rendering is correct.
- 2026-09-12 — Multi-turn dangling-tool-call bug confirmed fixed via 5 real
  queries across owner + procurement_manager personas.
- 2026-09-12 — No Claude Code available; workflow adapted to: Claude generates
  code in this chat → user runs locally (has real DB/network access) → pastes
  back output/errors → iterate. Git commit after each verified step.
- 2026-09-12 — First working `/chat` call verified end-to-end against the
  real DB (inventory_manager persona, min-stock query, correct answer).
- 2026-09-12 — Real schema turned out to be 27 tables, not 17: includes
  LangGraph's own checkpoint tables (already in use) and a working auth
  system (`users`, `refresh_tokens`). Agent's schema view scoped to the 16
  real business tables only.
- 2026-09-12 — Planning phase closed; sandbox lacks DB/deploy network access,
  so build/run/deploy work happens locally, not in this chat's sandbox.