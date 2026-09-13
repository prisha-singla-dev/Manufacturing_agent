import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import BadRequestError

load_dotenv(Path(__file__).with_name(".env"))
from backend.agent import build_graph
from backend.tools import PENDING_WRITES
from backend.db import pool

state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    state["graph"] = build_graph()
    yield
    pool.close()


app = FastAPI(lifespan=lifespan)

# Comma-separated list, e.g. "http://localhost:3000,https://your-app.vercel.app"
# Set ALLOWED_ORIGINS on the deployed backend once you have the Vercel URL.
allowed_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    persona: str  # 'owner' | 'procurement_manager' | 'inventory_manager'
    thread_id: str  # one per conversation; keep stable client-side per chat session


class ChatResponse(BaseModel):
    response_type: str
    text: str
    table: list[dict] | None = None
    chart: dict | None = None
    proposal_id: str | None = None


def _looks_like_markdown_table(text: str) -> bool:
    t = (text or "").lower()
    return t.count("\n|") > 1 or "|---" in t or t.count("\n-") > 3 or t.count("\n1.") > 0


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    graph = state["graph"]
    config = {"configurable": {"thread_id": req.thread_id}}
    try:
        result = graph.invoke(
            {"messages": [{"role": "user", "content": req.message}], "persona": req.persona, "final": None},
            config=config,
        )
    except BadRequestError as e:
        # This specific error means the thread's checkpointed history has an
        # AI message with a tool call that never got a matching response —
        # almost always caused by a connection drop mid-write in a past
        # turn, not something a retry of *this* turn can fix. The thread's
        # history is permanently in a bad state; only a fresh thread_id
        # recovers (the UI's "New chat" button does exactly that).
        print(f"[chat] thread {req.thread_id} appears corrupted (dangling tool_call): {e}")
        return ChatResponse(
            response_type="text",
            text="This conversation hit an internal error and can't continue. Please click \"New chat\" to start fresh — your other conversations aren't affected.",
        )
    final = result.get("final")
    if not final:
        # Agent didn't call RespondToUser (shouldn't normally happen) — fall
        # back to its last text so the user isn't left with nothing.
        last = result["messages"][-1]
        return ChatResponse(response_type="text", text=getattr(last, "content", "Sorry, I couldn't complete that."))

    # Known LLM non-determinism: even with an explicit prompt rule, the model
    # occasionally reverts to stuffing tabular data into `text` instead of
    # using response_type='table'. One retry only halves the odds of hitting
    # it again; two independent retries make it unlikely enough to accept.
    attempts = 0
    while final.get("response_type") == "text" and _looks_like_markdown_table(final.get("text", "")) and attempts < 2:
        attempts += 1
        print(f"[chat] thread {req.thread_id} produced markdown-in-text, retry {attempts}/2")
        correction = {
            "role": "user",
            "content": (
                "Your last answer put tabular data into a text response. "
                "Re-answer the same question using response_type='table' "
                "with the full rows in `table`, and a one-sentence summary "
                "in `text` only."
            ),
        }
        retry_result = graph.invoke(
            {"messages": [correction], "persona": req.persona, "final": None}, config=config
        )
        final = retry_result.get("final") or final

    return ChatResponse(**final)


@app.post("/confirm-write/{proposal_id}")
async def confirm_write(proposal_id: str):
    proposal = PENDING_WRITES.get(proposal_id)
    if not proposal:
        raise HTTPException(404, "No such proposal, or it already expired/executed.")
    try:
        with pool.connection() as conn:
            conn.execute(proposal["sql"])
            conn.commit()
        del PENDING_WRITES[proposal_id]
        return {"status": "executed", "explanation": proposal["explanation"]}
    except Exception as e:
        print(f"[confirm-write] FAILED for proposal {proposal_id}\n  sql={proposal['sql']}\n  error={e}")
        raise HTTPException(400, f"Write failed: {e}")


@app.get("/health")
async def health():
    return {"status": "ok"}