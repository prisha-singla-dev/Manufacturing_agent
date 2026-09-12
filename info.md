# Info - Manufacturing Inventory/Procurement Chat Agent

## Use case
A conversational (chat-based) agent for a manufacturing company's Postgres DB (17 tables, spanning **inventory** and **procurement**). Three personas query it:

- **Inventory manager** - stock levels, reorder points, warehouse movement, aging stock
- **Procurement manager** - purchase orders, supplier performance, lead times, pending approvals
- **Business owner** - cross-cutting: spend trends, stockout risk, supplier concentration, cost summaries

The agent must decide, per query, whether the best response is plain text, a table, or a chart - not just answer in text always.

**Bonus (not mandatory):** the agent can write to the DB (e.g., "reorder 200 units of X"), and the app can have authentication.

## Tech stack
- Frontend: Next.js
- Backend: FastAPI
- Agent: LangGraph (OpenAI models via provided API key)
- Tracing: LangSmith
- DB: Postgres (user-provided, 17 tables)
- Hosting: localhost primary; Vercel (frontend) / Railway or Render (backend) as stretch

## Constraints driving the design
- Tight message budget (~15-20 exchanges) → favor decisions made once and documented here, not re-discussed. Actual coding/running/deploying against the real DB happens in an environment with real network access (recommended: Claude Code), not this chat sandbox - this chat's role is plan + scaffolding + handoff spec.
- Shared/rate-limited API budget → keep the agent's tool-calling loop tight (avoid unnecessary re-planning turns), and prefer a smaller number of well-scoped tools over a sprawling toolset.

## Assumptions (stated up front, not re-litigated per phase unless something breaks them)
1. **Personas are selected, not authenticated** - a persona switch in the UI, no login flow, for the core build. Real auth remains optional (bonus); it does not gate deploy.
2. **Write-back is confirm-then-execute** - the agent proposes the exact SQL/action, the user must explicitly confirm in the UI before it runs. No silent writes, ever.
3. **Visualization decision is structured output, not vibes** - the agent's final response includes an explicit `response_type: text | table | chart` field (plus a `chart_type` when relevant) rather than the frontend trying to guess from prose.
   *Why:* keeps rendering deterministic and testable; the alternative (frontend sniffing the text for "looks like a table") is fragile and untestable.
4. **Schema is read dynamically, not hardcoded into the prompt** - the agent loads table/column metadata from the DB (or a cached schema doc) at startup.
   *Why:* the real 17-table schema wasn't available when scaffolding started; dynamic loading means swapping in the real schema later doesn't require re-architecting the agent.
5. **One SQL-execution tool, not per-table tools** - a single parameterized "run read query" tool (+ a separate gated "run write query" tool), rather than 17+ bespoke tools.
   *Why:* 17 tables with bespoke tools would bloat the toolset and the LangGraph planning overhead for little benefit; a well-described schema + one SQL tool is the standard, proven NL2SQL pattern and keeps latency down.
6. **No multi-tenant / row-level security** - single company, single DB, persona only changes *framing* of the query, not DB-level access control. *Why:* out of scope for a 3-user internal tool; would be real over-engineering here.

## Open questions (blocking real accuracy, not blocking progress)
- [ ] Real schema for the 17 tables (table names + purpose, or full DDL). Until provided, a fabricated but plausible inventory/procurement schema is used - flagged everywhere it's assumed.

---

## Phase log
*(Filled in as each phase completes - approach taken, alternatives considered, why.)*

### Phase 0 - Planning
- Approach: lock scope, assumptions, and phase plan before writing code, given the
  tight message budget and the sandbox's lack of DB/deploy access.
- Alternative considered: start coding immediately against a guessed schema.
  Rejected - rework risk if the real schema arrives mid-build is higher than the
  cost of one round of upfront planning.

### Phase 1 - Test cases + schema
- Approach: had the schema dumped locally (chat sandbox can't reach the DB
  network-wise) via a one-off `scripts/dump_schema.py` script, then drafted
  test cases against the real table/column names instead of the earlier
  guessed schema.
- Finding: 27 tables exist, not 17. 8 of them are LangGraph's own
  checkpoint/migration tables (already populated - this DB has been used by
  a running agent before) plus `users`/`refresh_tokens` for auth. Real
  business data is 16 tables (`inv_*`, `proc_*`).
- Decision: scope the agent's schema view (what gets put in its prompt) to
  just the 16 business tables. *Why:* the LLM doesn't need to know about its
  own persistence internals, and excluding `refresh_tokens`/`password_hash`
  keeps auth secrets out of the prompt entirely rather than relying on the
  model to "know" not to touch them.
- Decision: treat existing rows as shared/live, not disposable - inserts for
  demoing write-back are fine, deletes/edits to existing rows are not,
  because the shared-budget framing suggests this is a common environment,
  not a private sandbox.
- Alternative considered: fabricate a schema and ask user to reconcile later.
  Rejected once real schema was available - no reason to keep a placeholder
  once the real thing exists.

### Phase 2 - Backend skeleton
- Approach: FastAPI + a custom LangGraph `StateGraph` (not the prebuilt
  `create_react_agent`), because the response-typing requirement needed a
  deterministic "terminal tool" (`RespondToUser`) the graph can detect and
  route to `END` on - the prebuilt ReAct agent doesn't expose that hook
  cleanly.
- Approach: one generic `run_sql_read` tool (schema injected into the system
  prompt) rather than per-table tools. *Why:* 16 tables of bespoke tools
  would bloat tool-calling overhead and latency for no real accuracy gain -
  a well-described schema + one parameterized SQL tool is the standard
  NL2SQL pattern.
- Approach: write-back is two-step (`propose_write` stores a pending SQL
  string + explanation; a separate `/confirm-write/{id}` endpoint executes
  it). *Why:* never let the agent execute a write in the same turn it
  decided to - a human confirmation step is non-negotiable for anything that
  mutates real data.
- Approach: LangGraph checkpointing points at the **existing**
  `checkpoints`/`checkpoint_writes`/`checkpoint_blobs` tables rather than
  creating new ones. *Why:* they already exist and are populated - no reason
  to duplicate persistence infrastructure that's already there.
- Verified: `POST /chat` with an `inventory_manager` persona and a min-stock
  question returned a correct, DB-grounded text answer (no items currently
  below min stock - confirmed correct given the live data).
- Not yet verified: `table`/`chart` response types, the write-back path, and
  LangSmith trace visibility.
- **Bug found (2026-09-12):** tested 2 more real queries - agent returned
  `response_type: "text"` both times, hand-formatting the data as markdown
  tables / numbered lists inside `text` instead of populating the `table`
  field. Also silently truncated a 12+ row answer to 5 with "...and more."
- Fix applied: tightened `SYSTEM_PROMPT` in `agent.py` - explicit rule that
  >1 row of structured data MUST go through `response_type='table'` with the
  full row list in `table`, `text` reduced to a one-sentence summary only,
  and an explicit ban on "...and more" truncation (must aggregate in SQL
  instead of returning partial raw rows). Not yet re-verified against real
  queries.
- **Verified (2026-09-12):** re-ran the same queries plus a chart variant -
  text/table/chart all now route correctly, `table`/`chart` fields fully
  populated, no truncation. Fix confirmed working.
- **New bug found (2026-09-12), separate from the above:** the pending-POs
  table query returns duplicate rows (e.g. one PO tripled with identical
  values) - a join fan-out, not a typing issue. Summary text conflates "PO"
  count with "PO line" count. Queued as a Phase 5 fix (sharper prompt rule
  distinguishing PO vs PO-line granularity, and preferring aggregated SQL
  over raw joins) rather than blocking Phase 4 frontend work, since it's an
  orthogonal data-accuracy concern.
- **Third bug found + fixed (2026-09-12):** `finalize_node` extracted
  `RespondToUser`'s args but never returned a matching `ToolMessage`, so any
  2nd message in the same `thread_id` crashed OpenAI with a dangling
  tool_call error. Only surfaced via the frontend (which reuses one
  `thread_id` per persona across a whole conversation) - every curl test
  had used a fresh `thread_id`, masking it. *Why this matters for the
  approach log:* it's a reminder that testing via fresh IDs each time isn't
  equivalent to testing a real conversation - fixed `finalize_node` to
  always emit a `ToolMessage` per tool_call in the triggering message, not
  just extract data from it. Verified via 5 real multi-turn queries.

### Phase 3 - Response typing + write-back tool
- Same code as Phase 2's `tools.py`/`agent.py` - response typing and the
  write-back tool were built together, not sequentially, since they share
  the same `RespondToUser` terminal-tool mechanism. See Phase 2 log above
  for the approach and both bugs found there.
- Write-back (`propose_write` → `/confirm-write`) is code-complete but not
  yet run end-to-end against the real DB - that's test #11, in progress.

### Phase 4 - Frontend
- Approach: built with Next.js App Router, Tailwind, and Recharts - a thin
  client that trusts the backend's `response_type` completely rather than
  re-deriving it, since that logic is already tested server-side.
- Approach: one `thread_id` per persona, persisted in `localStorage`, so
  switching roles doesn't bleed conversation history across personas in the
  LangGraph checkpointer. *Why this mattered in practice:* this exact design
  choice is what surfaced the multi-turn `ToolMessage` bug above - a fresh
  `thread_id` per message (as curl testing did) would never have hit it.
- Added a "New chat" button that mints a fresh `thread_id` on demand - a
  direct response to hitting a corrupted-thread dead end during the
  multi-turn bug investigation; without it, a broken thread has no recovery
  path from the UI.
- **Redesign (2026-09-12), per user feedback that the first pass was "too
  basic":** replaced default Tailwind styling with an intentional palette
  and type system (IBM Plex Sans/Mono, steel/slate/ink tones) rather than
  generic SaaS-card defaults - justified by the subject matter (an internal
  tool for people reading PO numbers and item codes, not a consumer product)
  and reusing Plex Mono specifically for numeric/coded data, not as
  decoration. Added avatars, timestamps, an animated typing indicator, and
  clickable suggested-question chips for the empty state. User confirmed:
  "UI rendering is perfect."

### Phase 5 - Integration + full test-case pass
- Approach: rather than pasting each of the 11 test-matrix queries as a
  manual curl one at a time, built `scripts/test_queries.py` to run the
  whole matrix automatically and self-check for regressions of both bugs
  already found (markdown-in-text, duplicate rows by `id`) plus empty
  table/chart fields. *Why:* manual curl-by-curl doesn't scale to "test
  every possible query" without burning excessive back-and-forth, and the
  two real bugs found so far were both things a simple automated check
  could have caught immediately rather than requiring a human to notice the
  pattern in raw JSON.

### Phase 6 - Deploy
- **Reclassified from stretch to required (2026-09-12)**, gated on Phase 5
  passing cleanly. Not started yet.s)
- Hosting: localhost primary; Vercel (frontend) / Railway or Render (backend) as stretch

## Constraints driving the design
- Tight message budget (~15-20 exchanges) → favor decisions made once and documented
  here, not re-discussed. Actual coding/running/deploying against the real DB happens
  in an environment with real network access (recommended: Claude Code), not this chat
  sandbox - this chat's role is plan + scaffolding + handoff spec.
- Shared/rate-limited API budget → keep the agent's tool-calling loop tight (avoid
  unnecessary re-planning turns), and prefer a smaller number of well-scoped tools
  over a sprawling toolset.

## Assumptions (stated up front, not re-litigated per phase unless something breaks them)
1. **Personas are selected, not authenticated** - a persona switch in the UI, no login
   flow, for the core build. Real auth is a Phase 6 stretch item.
2. **Write-back is confirm-then-execute** - the agent proposes the exact SQL/action,
   the user must explicitly confirm in the UI before it runs. No silent writes, ever.
3. **Visualization decision is structured output, not vibes** - the agent's final
   response includes an explicit `response_type: text | table | chart` field (plus
   a `chart_type` when relevant) rather than the frontend trying to guess from prose.
   *Why:* keeps rendering deterministic and testable; the alternative (frontend
   sniffing the text for "looks like a table") is fragile and untestable.
4. **Schema is read dynamically, not hardcoded into the prompt** - the agent loads
   table/column metadata from the DB (or a cached schema doc) at startup.
   *Why:* the real 17-table schema wasn't available when scaffolding started; dynamic
   loading means swapping in the real schema later doesn't require re-architecting
   the agent.
5. **One SQL-execution tool, not per-table tools** - a single parameterized
   "run read query" tool (+ a separate gated "run write query" tool), rather than
   17+ bespoke tools.
   *Why:* 17 tables with bespoke tools would bloat the toolset and the LangGraph
   planning overhead for little benefit; a well-described schema + one SQL tool is
   the standard, proven NL2SQL pattern and keeps latency down.
6. **No multi-tenant / row-level security** - single company, single DB, persona only
   changes *framing* of the query, not DB-level access control.
   *Why:* out of scope for a 3-user internal tool; would be real over-engineering here.

## Open questions (blocking real accuracy, not blocking progress)
- [ ] Real schema for the 17 tables (table names + purpose, or full DDL). Until
      provided, a fabricated but plausible inventory/procurement schema is used -
      flagged everywhere it's assumed.

---

## Phase log
*(Filled in as each phase completes - approach taken, alternatives considered, why.)*

### Phase 0 - Planning
- Approach: lock scope, assumptions, and phase plan before writing code, given the
  tight message budget and the sandbox's lack of DB/deploy access.
- Alternative considered: start coding immediately against a guessed schema.
  Rejected - rework risk if the real schema arrives mid-build is higher than the
  cost of one round of upfront planning.

### Phase 1 - Test cases + schema
- Approach: had the schema dumped locally (chat sandbox can't reach the DB
  network-wise) via a one-off `scripts/dump_schema.py` script, then drafted
  test cases against the real table/column names instead of the earlier
  guessed schema.
- Finding: 27 tables exist, not 17. 8 of them are LangGraph's own
  checkpoint/migration tables (already populated - this DB has been used by
  a running agent before) plus `users`/`refresh_tokens` for auth. Real
  business data is 16 tables (`inv_*`, `proc_*`).
- Decision: scope the agent's schema view (what gets put in its prompt) to
  just the 16 business tables. *Why:* the LLM doesn't need to know about its
  own persistence internals, and excluding `refresh_tokens`/`password_hash`
  keeps auth secrets out of the prompt entirely rather than relying on the
  model to "know" not to touch them.
- Decision: treat existing rows as shared/live, not disposable - inserts for
  demoing write-back are fine, deletes/edits to existing rows are not,
  because the shared-budget framing suggests this is a common environment,
  not a private sandbox.
- Alternative considered: fabricate a schema and ask user to reconcile later.
  Rejected once real schema was available - no reason to keep a placeholder
  once the real thing exists.

### Phase 2 - Backend skeleton
- Approach: FastAPI + a custom LangGraph `StateGraph` (not the prebuilt
  `create_react_agent`), because the response-typing requirement needed a
  deterministic "terminal tool" (`RespondToUser`) the graph can detect and
  route to `END` on - the prebuilt ReAct agent doesn't expose that hook
  cleanly.
- Approach: one generic `run_sql_read` tool (schema injected into the system
  prompt) rather than per-table tools. *Why:* 16 tables of bespoke tools
  would bloat tool-calling overhead and latency for no real accuracy gain -
  a well-described schema + one parameterized SQL tool is the standard
  NL2SQL pattern.
- Approach: write-back is two-step (`propose_write` stores a pending SQL
  string + explanation; a separate `/confirm-write/{id}` endpoint executes
  it). *Why:* never let the agent execute a write in the same turn it
  decided to - a human confirmation step is non-negotiable for anything that
  mutates real data.
- Approach: LangGraph checkpointing points at the **existing**
  `checkpoints`/`checkpoint_writes`/`checkpoint_blobs` tables rather than
  creating new ones. *Why:* they already exist and are populated - no reason
  to duplicate persistence infrastructure that's already there.
- Verified: `POST /chat` with an `inventory_manager` persona and a min-stock
  question returned a correct, DB-grounded text answer (no items currently
  below min stock - confirmed correct given the live data).
- Not yet verified: `table`/`chart` response types, the write-back path, and
  LangSmith trace visibility.

### Phase 3 - Response typing + write-back tool
*(pending)*

### Phase 4 - Frontend
*(pending)*

### Phase 5 - Integration + test-case pass
*(pending)*

### Phase 6 - Stretch: auth + cloud deploy
*(pending)*