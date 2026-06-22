"""
The agent graph: state schema, the agent node (calls the LLM), the tool
node (executes whatever the LLM decided to call), and the routing logic
between them.

Flow: agent -> (has tool calls? -> tools -> back to agent) -> (no tool
calls? -> END). This loop is what lets the agent chain multiple tool
calls before answering -- e.g. look up the customer, then look up their
order, then answer, all before a single reply reaches the user.
"""

import os
from typing import Annotated, Optional
from typing_extensions import TypedDict

from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import interrupt, Command
from langchain_core.messages import SystemMessage, ToolMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row

from llm_tools import ALL_TOOLS

load_dotenv()

# Override with a line in .env, e.g. GEMINI_MODEL=gemini-2.0-flash
# Different models sit in separate quota buckets, so this is the fastest
# way to test whether another model has free-tier headroom.
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in backend/.env")

TOOLS_BY_NAME = {t.name: t for t in ALL_TOOLS}

# These touch money or an order's actual status. Everything else the
# agent can call freely; these two pause for a human decision first.
SENSITIVE_TOOLS = {"process_refund", "cancel_order"}

SYSTEM_PROMPT = """You are a customer support agent for Nimbus Gear, an electronics retailer.

Be concise, warm, and professional. Use tools to look up real information
instead of guessing -- never invent order numbers, ticket numbers, or
policy details that a tool hasn't actually returned to you.

Rules:
- You CAN propose a refund or order cancellation using process_refund / cancel_order
  when you're confident the order qualifies under policy -- but these always
  pause for human approval before they execute, so propose them when
  appropriate rather than avoiding them.
- Call process_refund or cancel_order ALONE in a turn, never bundled with
  other tool calls.
- For anything more ambiguous or complicated than a clear-cut refund or
  cancellation, use escalate instead.
- If you're not confident an answer is correct, search the knowledge base first.
- At the start of a conversation, look up the customer's history so you have context.
"""


class AgentState(TypedDict):
    # add_messages is a reducer: each node's return value gets APPENDED
    # to this list rather than replacing it. That's what makes message
    # history accumulate turn over turn instead of resetting each call.
    messages: Annotated[list, add_messages]
    customer_id: Optional[int]


def build_llm():
    return ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        temperature=0.3,
    ).bind_tools(ALL_TOOLS)


def agent_node(state: AgentState, llm) -> dict:
    messages = state["messages"]
    customer_id = state.get("customer_id")

    # Only prepend the system message once per thread -- on later turns
    # it's already sitting in the checkpointed history.
    if not any(isinstance(m, SystemMessage) for m in messages):
        content = SYSTEM_PROMPT
        if customer_id is not None:
            content += f"\n\nYou are currently speaking with customer_id={customer_id}. Use this exact ID whenever a tool requires one."
        messages = [SystemMessage(content=content)] + messages

    try:
        response = llm.invoke(messages)
    except Exception as e:
        # A 429 (rate limit) or any other API hiccup shouldn't take the
        # whole conversation down with it. Surface it as a normal-looking
        # agent message instead of an unhandled exception.
        from langchain_core.messages import AIMessage
        response = AIMessage(
            content=(
                "I'm having trouble reaching my reasoning engine right now "
                f"({type(e).__name__}). Please try again in a moment."
            )
        )
    return {"messages": [response]}


def tool_node(state: AgentState) -> dict:
    last_message = state["messages"][-1]
    results = []
    for call in last_message.tool_calls:
        tool_fn = TOOLS_BY_NAME[call["name"]]
        try:
            output = tool_fn.invoke(call["args"])
        except Exception as e:
            output = f"Tool error: {e}"
        results.append(ToolMessage(content=str(output), tool_call_id=call["id"]))
    return {"messages": results}


def human_approval_node(state: AgentState) -> dict:
    """Gate for process_refund / cancel_order. interrupt() is the very
    first thing that runs -- nothing with a side effect happens before
    it, so if this node re-executes from the top after resume (which it
    does, per LangGraph's resume semantics), nothing gets double-run.
    """
    last_message = state["messages"][-1]
    sensitive_call = next(
        c for c in last_message.tool_calls if c["name"] in SENSITIVE_TOOLS
    )

    decision = interrupt({
        "tool": sensitive_call["name"],
        "args": sensitive_call["args"],
    })
    approved = decision is True or (isinstance(decision, str) and decision.strip().lower() in ("y", "yes", "approve"))

    results = []
    if approved:
        tool_fn = TOOLS_BY_NAME[sensitive_call["name"]]
        try:
            output = tool_fn.invoke(sensitive_call["args"])
        except Exception as e:
            output = f"Tool error: {e}"
        results.append(ToolMessage(content=str(output), tool_call_id=sensitive_call["id"]))
    else:
        results.append(ToolMessage(
            content=(
                "A human reviewer declined this action. Do not retry it. "
                "Tell the customer it needs manual review and, if appropriate, "
                "create a ticket instead."
            ),
            tool_call_id=sensitive_call["id"],
        ))

    # Any OTHER tool calls bundled in the same turn run normally, AFTER
    # the interrupt -- safe, since they only happen post-resume.
    for call in last_message.tool_calls:
        if call["name"] in SENSITIVE_TOOLS:
            continue
        tool_fn = TOOLS_BY_NAME[call["name"]]
        try:
            output = tool_fn.invoke(call["args"])
        except Exception as e:
            output = f"Tool error: {e}"
        results.append(ToolMessage(content=str(output), tool_call_id=call["id"]))

    return {"messages": results}


def route_after_agent(state: AgentState) -> str:
    last_message = state["messages"][-1]
    calls = getattr(last_message, "tool_calls", None)
    if not calls:
        return END
    if any(c["name"] in SENSITIVE_TOOLS for c in calls):
        return "human_approval"
    return "tools"


def build_graph():
    llm = build_llm()

    graph = StateGraph(AgentState)
    graph.add_node("agent", lambda state: agent_node(state, llm))
    graph.add_node("tools", tool_node)
    graph.add_node("human_approval", human_approval_node)

    graph.set_entry_point("agent")
    graph.add_conditional_edges(
        "agent", route_after_agent,
        {"tools": "tools", "human_approval": "human_approval", END: END},
    )
    graph.add_edge("tools", "agent")
    graph.add_edge("human_approval", "agent")

    # PostgresSaver is LangGraph's officially-supported production
    # checkpointer -- persists every turn to the same Postgres database
    # as the business data, keyed by thread_id. The connection pool
    # (rather than one bare connection) is what makes this safe under
    # concurrent requests, which a single sqlite3 connection wasn't.
    pool = ConnectionPool(
        conninfo=DATABASE_URL,
        max_size=10,
        kwargs={"autocommit": True, "row_factory": dict_row},
    )
    checkpointer = PostgresSaver(pool)
    checkpointer.setup()  # idempotent -- creates checkpoint tables if missing
    return graph.compile(checkpointer=checkpointer)