# Backend — run locally

```bash
cd backend
python -m venv venv
venv\Scripts\activate        
pip install -r requirements.txt
copy .env.example .env      
uvicorn backend.main:app --reload --port 8000 --app-dir ..

# else
cd..
cd ..
uvicorn backend.main:app --reload --port 8000
```

Test it without a frontend first:

Test the server
Health check - 
```bash
curl.exe http://localhost:8000/health
```

```bash
curl.exe -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d "{\"message\":\"Which items are below their min stock level?\",\"persona\":\"inventory_manager\",\"thread_id\":\"test-1\"}"

curl.exe -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d "{\"message\":\"show vendor-wise PO value\",\"persona\":\"inventory_manager\",\"thread_id\":\"test-2\"}"

curl.exe -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d "{\"message\":\"which POs are pending receipt\",\"persona\":\"inventory_manager\",\"thread_id\":\"test-3\"}"

curl.exe -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d "{\"message\":\"compare total PO value by vendor as a chart\",\"persona\":\"procurement_manager\",\"thread_id\":\"test-4\"}"

curl.exe -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d "{\"message\":\"Record a new transaction received 50 units of steel at Falcon Steels Pvt. Ltd\",\"persona\":\"procurement_manager\",\"thread_id\":\"test-5\"}"

```

If anything errors, paste the full traceback back into chat — that's the fastest way for us to fix it since I can't run this against your DB myself.

## Notes
- `thread_id` should be a stable per-conversation id (e.g. a UUID generated
  once in the frontend and reused for that chat session) — LangGraph uses it
  to load prior turns from the existing `checkpoints` table.
- Rows returned by `run_sql_read` are capped at 200 — if a query legitimately
  needs more, the agent should aggregate in SQL instead.
- `WRITABLE_TABLES` in `db.py` is intentionally short (transactions, POs, PO
  lines, receipts). Add to it only if a test case needs another table
  written to.