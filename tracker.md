# Tracker — Manufacturing Chat Agent

Legend: ✅ done · 🔄 in progress · ⬜ not started · ⏭️ skipped

## Phase 0 — Planning
- ✅ Use case captured, feasibility confirmed
- ✅ Assumptions documented (info.md)
- ✅ Phase plan agreed
- ✅ info.md created
- ✅ tracker.md created
- ✅ Real schema provided (27 tables — includes LangGraph + auth infra already set up)

## Phase 1 — Test cases + schema
- ✅ 11 draft test cases across all 3 personas
- ✅ Schema confirmed real; scoped agent's view to 16 business tables
- ✅ Persona → role mapping confirmed via users table
- ✅ Automated test runner built (`scripts/test_queries.py`)
- ✅ Seed data — not needed; all 11 test cases returned real, demo-worthy answers as-is

## Phase 2 — Backend skeleton
- ✅ FastAPI app scaffolded (`/chat`, `/confirm-write`, `/health`)
- ✅ LangGraph agent graph defined
- ✅ SQL read tool — verified
- ✅ Reuses existing `checkpoints` tables for persistence
- ✅ Chart/table response-typing bug — found, fixed, verified
- ✅ Multi-turn dangling-tool-call bug — found, fixed, verified (5 real queries)
- ✅ Write-back null-id bug — found (INSERT omitted `id`, which has no DB
  default on these tables), fixed at both the tool level (propose_write now
  rejects an INSERT missing `id` with an actionable error) and the prompt
  level. **Verified — write executed successfully end-to-end via the UI.**
- ✅ Connection-drop bug — a long-lived single checkpointer connection died
  against Railway's proxy (`SSL SYSCALL error: EOF detected`), corrupting
  that thread's history. Fixed by sharing the health-checked connection pool
  between the checkpointer and the SQL tool. Added a graceful fallback for
  any future corrupted-thread error (clear message + "New chat" prompt
  instead of a raw 500).
- ✅ LangSmith tracing confirmed visually — full waterfall (agent → tool
  calls → route → final) visible per request, including exact SQL run

## Phase 3 — Response typing + write-back tool
- ✅ Structured response schema — implemented and verified
- ✅ Visualization-decision logic — verified across all 11 test-matrix queries
- ✅ Write-back tool (propose → confirm → execute) — **verified end-to-end**, test transaction inserted successfully
- ✅ Guardrail confirmed: write tool cannot execute without `/confirm-write`

## Phase 4 — Frontend
- ✅ Next.js chat UI, table/chart renderers, write-confirm UI
- ✅ Verified against live backend, multi-turn
- ✅ UI redesign — user-confirmed "rendering is perfect"

## Phase 5 — Integration + full test-case pass
- ✅ All 11 test-matrix queries clean on first full run
- ✅ **Test #11 (write-back) — fully verified end-to-end**, including actual `/confirm-write` execution (confirmed via UI green success message)
- ⏭️ Duplicate-row bug (pending POs) — **not currently reproducible**: DB now shows 0 pending POs (data has changed since first found), so nothing to re-test against right now. Not forgotten — if pending POs reappear later and duplicates return, revisit `proc_po_lines`/`proc_po_receipts` join logic.
- ✅ LangSmith traces reviewed — confirmed working, full waterfall visible
- 🔄 **Regression found on 2nd full rerun:** vendor-wise PO value question
  reverted to markdown-in-text (LLM non-determinism, not a logic bug) —
  fixed with a code-level one-shot self-correction retry in `/chat`.
  **Verified on 3rd rerun** — self-corrected to a proper table.
- ✅ **Payment-tranches bug fixed and verified** — retry-on-SQL-error prompt
  rule resolved the silent failure; now returns a correct answer.
- ✅ **Self-correction detection gap fixed:** runtime check only caught
  pipe-tables/bullet-dashes, missed numbered lists (`1. ...`, `2. ...`) that
  `test_queries.py` already caught — brought the two checks in sync. Fix
  applied, awaiting one more rerun to confirm.

## Phase 6 — Deploy (required, gated on Phase 5 fully green)
- ⬜ Cloud deploy: backend (Railway or Render)
- ⬜ Cloud deploy: frontend (Vercel)
- ⬜ End-to-end smoke test against deployed URLs
- ⬜ Authentication — BONUS, optional, does not block deploy

---
## Decisions log (running, most recent first)
- 2026-09-12 — Test #11 (write-back) fully verified end-to-end — test
  transaction proposed, confirmed, and executed successfully via the UI.
- 2026-09-12 — Connection-drop bug fixed: checkpointer now shares the
  health-checked connection pool instead of holding one dedicated raw
  connection open for the app's lifetime. Added graceful handling for any
  future corrupted-thread error (clear message instead of a 500 crash).
- 2026-09-12 — Write-back null-id bug found and fixed: `inv_transactions`
  and the other writable tables have no DB-side default for `id` (unlike
  `users`), so the agent's INSERT left it null. Fixed with a code-level
  guard in `propose_write` (rejects INSERT missing `id`, tells the agent to
  use `gen_random_uuid()::text`) plus a matching system-prompt rule.
- 2026-09-12 — Full automated test matrix (11/11) came back clean — no
  markdown-in-text, no empty table/chart fields, no duplicate rows detected
  in this run's data state.
- 2026-09-12 — Deploy reclassified from "stretch" to required.
- 2026-09-12 — Frontend UI redesigned per user feedback — industrial design
  system, user-confirmed correct.
- 2026-09-12 — Multi-turn dangling-tool-call bug fixed and verified.
- 2026-09-12 — No Claude Code available; workflow is Claude generates code →
  user runs locally → pastes output/errors → iterate.
- 2026-09-12 — Real schema is 27 tables (16 business + LangGraph/auth
  internals already in place).