# Frontend - run locally

```bash
cd frontend
npm install
copy .env.local.example .env.local
npm run dev
```

Open http://localhost:3000. Make sure the backend (`uvicorn main:app --reload
--port 8000`) is running first - the frontend calls it directly, no proxy.

## What it does
- Persona switcher (top right) - each persona gets its own `thread_id`
  (stored in `localStorage`), so switching roles doesn't mix conversation
  history in the LangGraph checkpointer.
- Renders `text` inline, `table` as a scrollable HTML table, `chart` via
  Recharts (bar/line/pie based on `chart_type`), and `confirm_write` as an
  amber confirmation card that calls `/confirm-write/{proposal_id}` only
  when the user clicks the button - never automatically.

## Known gaps (expected at this phase)
- No loading skeleton, no error retry - just a plain error string in chat.
- No auth/login UI yet - persona is just a dropdown, matching the backend's
  current no-auth assumption.
- Chart x-axis labels aren't sorted/truncated for very long vendor name
  lists - fine for demo scale, would need a treatment pass for 100+ bars.
