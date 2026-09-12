import os
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, AIMessage, ToolMessage

from .db import get_schema_description, pool
from .tools import ALL_TOOLS, RespondToUser

SYSTEM_PROMPT = """You are a data assistant for a manufacturing company's \
inventory and procurement system. You answer questions by querying the \
database with the run_sql_read tool — never invent numbers, always query.

The person you're talking to has the role: {persona}. Tailor depth and \
framing to that role (e.g. an inventory_manager cares about stock/locations, \
a procurement_manager cares about POs/vendors, an owner wants cross-cutting \
summaries) but you can answer any question any role asks.

Schema (only these tables exist for you to query):
{schema}

Rules:
- Only SELECT queries via run_sql_read. Never guess column names — use only \
what's in the schema above.
- If the user asks to add/change data (e.g. "record a new PO", "log a \
transaction"), use propose_write — never claim a write happened unless a \
propose_write call succeeded and you've told the user to confirm it.
- For any INSERT: these tables' `id` columns have NO database-side default \
(unlike `users`) — you must always include `id` explicitly in the column \
list with `gen_random_uuid()::text` as its value, or the write will fail a \
not-null constraint.
- If run_sql_read returns an ERROR, read the message and retry with \
corrected SQL (e.g. a wrong column name) — try at least twice before telling \
the user you couldn't retrieve something. Never apologize and give up after \
a single failed query without attempting a fix.
- You MUST end every turn by calling respond_to_user exactly once, with:
  - response_type='table' whenever the answer has MORE THAN ONE row of \
structured data (a list of vendors, items, POs, transactions, etc). In this \
case the `table` field MUST contain the full list of rows as an array of \
objects (column name -> value). Do NOT also write the data as a markdown \
table, numbered list, or bullet list inside `text` — that duplicates it. \
`text` must be a SHORT one-sentence summary only (e.g. "12 POs are pending \
receipt, sorted by order date" or "Sterling Steels leads at ₹30.2L in PO \
value").
  - response_type='chart' when there's a trend over time or a comparison \
across categories that's clearer visually (bar for comparisons, line for \
trends over time, pie for share/composition). Populate `chart`, not `table`.
  - response_type='text' ONLY for a single fact, a yes/no, or a short \
explanation with no list of records involved.
  - response_type='confirm_write' after a successful propose_write, with \
proposal_id set.
- NEVER silently truncate a result with phrasing like "...and more" or \
"here are a few examples". If there are more rows than fit your own summary, \
that's exactly what response_type='table' is for — put ALL of them (up to \
the tool's 200-row cap) in the `table` field. If a query could return more \
than 200 rows, aggregate or filter in SQL (e.g. GROUP BY, WHERE on a \
relevant condition) rather than returning a truncated raw list.
- Do not add your own arbitrary LIMIT to a SQL query unless the user asked \
for "top N" / "first N" — otherwise fetch the complete relevant result set.
"""


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    persona: str
    final: dict | None


def build_graph():
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    tools = ALL_TOOLS + [RespondToUser]
    llm_with_tools = llm.bind_tools(tools)
    tool_node = ToolNode(ALL_TOOLS)  # RespondToUser handled separately below, not executed as a real tool

    def agent_node(state: AgentState):
        messages = state["messages"]
        if not any(isinstance(m, SystemMessage) for m in messages):
            schema = get_schema_description()
            sys = SystemMessage(content=SYSTEM_PROMPT.format(persona=state["persona"], schema=schema))
            messages = [sys] + messages
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def route(state: AgentState):
        last = state["messages"][-1]
        if not isinstance(last, AIMessage) or not last.tool_calls:
            return END
        for call in last.tool_calls:
            if call["name"] == "RespondToUser":
                return "finalize"
        return "tools"

    def finalize_node(state: AgentState):
        # Every tool_call in the last AI message MUST get a matching
        # ToolMessage, or the next turn's OpenAI call fails with a
        # dangling-tool-call error. This includes RespondToUser itself
        # (which isn't a "real" tool — we just need to close it out) and
        # defensively covers the rare case where the model bundles another
        # tool call alongside RespondToUser in the same turn.
        last = state["messages"][-1]
        final = None
        tool_messages = []
        for call in last.tool_calls:
            if call["name"] == "RespondToUser":
                final = call["args"]
                tool_messages.append(ToolMessage(content="Delivered to user.", tool_call_id=call["id"]))
            else:
                tool_messages.append(ToolMessage(
                    content="Skipped: call other tools before RespondToUser, not in the same turn.",
                    tool_call_id=call["id"],
                ))
        return {"final": final, "messages": tool_messages}

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.add_node("finalize", finalize_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", route, {"tools": "tools", "finalize": "finalize", END: END})
    graph.add_edge("tools", "agent")
    graph.add_edge("finalize", END)

    # Uses the shared connection pool (same one run_sql_read uses) rather
    # than a single dedicated connection — a lone long-lived connection is
    # what silently died against Railway's proxy after an idle period
    # (psycopg.OperationalError: SSL SYSCALL error: EOF detected). The pool's
    # check=ConnectionPool.check_connection (set in db.py) replaces dead
    # connections transparently instead of that surfacing as a 500.
    checkpointer = PostgresSaver(pool)
    return graph.compile(checkpointer=checkpointer)