import os
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, AIMessage

from .db import get_schema_description
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
- You MUST end every turn by calling respond_to_user exactly once, with:
  - response_type='table' when the natural answer is a list of records
  - response_type='chart' when there's a trend or comparison across \
categories worth visualizing (bar for comparisons, line for trends over \
time, pie for share/composition)
  - response_type='text' for a single fact or short explanation
  - response_type='confirm_write' after a successful propose_write, with \
proposal_id set
- Keep the `text` field populated always, even for table/chart responses — \
it's the spoken summary alongside the data.
"""


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    persona: str
    final: dict | None


def build_graph(database_url: str):
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
        last = state["messages"][-1]
        for call in last.tool_calls:
            if call["name"] == "RespondToUser":
                return {"final": call["args"]}
        return {}

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.add_node("finalize", finalize_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", route, {"tools": "tools", "finalize": "finalize", END: END})
    graph.add_edge("tools", "agent")
    graph.add_edge("finalize", END)

    # Reuses the checkpoints/checkpoint_writes/checkpoint_blobs tables that
    # already exist in this DB — no setup() call needed, they're in place.
    checkpointer_cm = PostgresSaver.from_conn_string(database_url)
    checkpointer = checkpointer_cm.__enter__()  # kept open for app lifetime; see main.py lifespan

    return graph.compile(checkpointer=checkpointer), checkpointer_cm