# Info — Manufacturing Inventory/Procurement Chat Agent

## Use case
A conversational (chat-based) agent for a manufacturing company's Postgres DB
(17 tables, spanning **inventory** and **procurement**). Three personas query it:

- **Inventory manager** — stock levels, reorder points, warehouse movement, aging stock
- **Procurement manager** — purchase orders, supplier performance, lead times, pending approvals
- **Business owner** — cross-cutting: spend trends, stockout risk, supplier concentration, cost summaries

The agent must decide, per query, whether the best response is plain text, a table,
or a chart — not just answer in text always.

**Bonus (not mandatory):** the agent can write to the DB (e.g., "reorder 200 units of X"),
and the app can have authentication.

## Tech stack
- Frontend: Next.js
- Backend: FastAPI
- Agent: LangGraph (OpenAI models via provided API key)
- Tracing: LangSmith
- DB: Postgres (user-provided, 17 tables)
- Hosting: localhost primary; Vercel (frontend) / Railway or Render (backend) as stretch

## Constraints driving the design
- Tight message budget (~15-20 exchanges) → favor decisions made once and documented
  here, not re-discussed. Actual coding/running/deploying against the real DB happens
  in an environment with real network access (recommended: Claude Code), not this chat
  sandbox — this chat's role is plan + scaffolding + handoff spec.
- Shared/rate-limited API budget → keep the agent's tool-calling loop tight (avoid
  unnecessary re-planning turns), and prefer a smaller number of well-scoped tools
  over a sprawling toolset.

## Assumptions (stated up front, not re-litigated per phase unless something breaks them)
1. **Personas are selected, not authenticated** — a persona switch in the UI, no login
   flow, for the core build. Real auth is a Phase 6 stretch item.
2. **Write-back is confirm-then-execute** — the agent proposes the exact SQL/action,
   the user must explicitly confirm in the UI before it runs. No silent writes, ever.
3. **Visualization decision is structured output, not vibes** — the agent's final
   response includes an explicit `response_type: text | table | chart` field (plus
   a `chart_type` when relevant) rather than the frontend trying to guess from prose.
   *Why:* keeps rendering deterministic and testable; the alternative (frontend
   sniffing the text for "looks like a table") is fragile and untestable.
4. **Schema is read dynamically, not hardcoded into the prompt** — the agent loads
   table/column metadata from the DB (or a cached schema doc) at startup.
   *Why:* the real 17-table schema wasn't available when scaffolding started; dynamic
   loading means swapping in the real schema later doesn't require re-architecting
   the agent.
5. **One SQL-execution tool, not per-table tools** — a single parameterized
   "run read query" tool (+ a separate gated "run write query" tool), rather than
   17+ bespoke tools.
   *Why:* 17 tables with bespoke tools would bloat the toolset and the LangGraph
   planning overhead for little benefit; a well-described schema + one SQL tool is
   the standard, proven NL2SQL pattern and keeps latency down.
6. **No multi-tenant / row-level security** — single company, single DB, persona only
   changes *framing* of the query, not DB-level access control.
   *Why:* out of scope for a 3-user internal tool; would be real over-engineering here.

## Open questions (blocking real accuracy, not blocking progress)
- [ ] Real schema for the 17 tables (table names + purpose, or full DDL). Until
      provided, a fabricated but plausible inventory/procurement schema is used —
      flagged everywhere it's assumed.

---

## Phase log
*(Filled in as each phase completes — approach taken, alternatives considered, why.)*

### Phase 0 — Planning
- Approach: lock scope, assumptions, and phase plan before writing code, given the
  tight message budget and the sandbox's lack of DB/deploy access.
- Alternative considered: start coding immediately against a guessed schema.
  Rejected — rework risk if the real schema arrives mid-build is higher than the
  cost of one round of upfront planning.

### Phase 1 — Test cases + schema
- Approach: had the schema dumped locally (chat sandbox can't reach the DB
  network-wise) via a one-off `scripts/dump_schema.py` script, then drafted
  test cases against the real table/column names instead of the earlier
  guessed schema.
- Finding: 27 tables exist, not 17. 8 of them are LangGraph's own
  checkpoint/migration tables (already populated — this DB has been used by
  a running agent before) plus `users`/`refresh_tokens` for auth. Real
  business data is 16 tables (`inv_*`, `proc_*`).
- Decision: scope the agent's schema view (what gets put in its prompt) to
  just the 16 business tables. *Why:* the LLM doesn't need to know about its
  own persistence internals, and excluding `refresh_tokens`/`password_hash`
  keeps auth secrets out of the prompt entirely rather than relying on the
  model to "know" not to touch them.
- Decision: treat existing rows as shared/live, not disposable — inserts for
  demoing write-back are fine, deletes/edits to existing rows are not,
  because the shared-budget framing suggests this is a common environment,
  not a private sandbox.
- Alternative considered: fabricate a schema and ask user to reconcile later.
  Rejected once real schema was available — no reason to keep a placeholder
  once the real thing exists.

### Phase 2 — Backend skeleton
- Approach: FastAPI + a custom LangGraph `StateGraph` (not the prebuilt
  `create_react_agent`), because the response-typing requirement needed a
  deterministic "terminal tool" (`RespondToUser`) the graph can detect and
  route to `END` on — the prebuilt ReAct agent doesn't expose that hook
  cleanly.
- Approach: one generic `run_sql_read` tool (schema injected into the system
  prompt) rather than per-table tools. *Why:* 16 tables of bespoke tools
  would bloat tool-calling overhead and latency for no real accuracy gain —
  a well-described schema + one parameterized SQL tool is the standard
  NL2SQL pattern.
- Approach: write-back is two-step (`propose_write` stores a pending SQL
  string + explanation; a separate `/confirm-write/{id}` endpoint executes
  it). *Why:* never let the agent execute a write in the same turn it
  decided to — a human confirmation step is non-negotiable for anything that
  mutates real data.
- Approach: LangGraph checkpointing points at the **existing**
  `checkpoints`/`checkpoint_writes`/`checkpoint_blobs` tables rather than
  creating new ones. *Why:* they already exist and are populated — no reason
  to duplicate persistence infrastructure that's already there.
- Verified: `POST /chat` with an `inventory_manager` persona and a min-stock
  question returned a correct, DB-grounded text answer (no items currently
  below min stock — confirmed correct given the live data).
- Not yet verified: `table`/`chart` response types, the write-back path, and
  LangSmith trace visibility.

### Phase 3 — Response typing + write-back tool
*(pending)*

### Phase 4 — Frontend
*(pending)*

### Phase 5 — Integration + test-case pass
*(pending)*

### Phase 6 — Stretch: auth + cloud deploy
*(pending)*