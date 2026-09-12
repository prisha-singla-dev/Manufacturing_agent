import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

from .agent import build_graph
from .tools import PENDING_WRITES
from .db import pool

DATABASE_URL = os.environ["DATABASE_URL"]

state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    graph, checkpointer_cm = build_graph(DATABASE_URL)
    state["graph"] = graph
    yield
    checkpointer_cm.__exit__(None, None, None)
    pool.close()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    graph = state["graph"]
    config = {"configurable": {"thread_id": req.thread_id}}
    result = graph.invoke(
        {"messages": [{"role": "user", "content": req.message}], "persona": req.persona, "final": None},
        config=config,
    )
    final = result.get("final")
    if not final:
        # Agent didn't call RespondToUser (shouldn't normally happen) - fall
        # back to its last text so the user isn't left with nothing.
        last = result["messages"][-1]
        return ChatResponse(response_type="text", text=getattr(last, "content", "Sorry, I couldn't complete that."))
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
        raise HTTPException(400, f"Write failed: {e}")


@app.get("/health")
async def health():
    return {"status": "ok"}