"""
Long-term memory: the part that makes the agent remember a customer
across DIFFERENT conversations, not just within one.

The short-term checkpointer (graph.py) keeps full message history per
thread -- great within a session, but it's not something you'd want an
LLM reading cold at the start of conversation #47. This module condenses
a finished conversation into a short running summary stored in
customer_memory, which IS small enough to drop into a system prompt
every time.

This intentionally runs OUTSIDE the graph, triggered by the calling
application (CLI now, the FastAPI endpoint later) when a session ends --
"when a conversation is over" isn't something the graph itself can
detect, only the application talking to it knows that.
"""

import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent / "db"))
from tools import get_customer_memory, update_customer_memory

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

# Same override as graph.py -- these used to be two independent hardcoded
# "gemini-2.5-flash" strings, which meant switching models in .env to
# dodge a quota wall silently did nothing here. One source of truth now.
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

SUMMARY_PROMPT = """You maintain short-term notes a support agent reads before \
talking to a returning customer. You are NOT writing a transcript -- you're \
writing the 2-4 sentences a busy human agent would actually want to see.

Existing notes on this customer (may be empty if this is their first \
conversation):
---
{existing_notes}
---

Transcript of the conversation that just ended:
---
{transcript}
---

Write an UPDATED set of notes that folds in anything from this conversation \
worth remembering, combined with whatever from the existing notes is still \
relevant. Prioritize: recurring problems, unresolved issues, anything \
escalated, and notable sentiment (frustrated, satisfied, etc). Drop routine \
successful interactions that don't need follow-up. If nothing in this \
conversation is worth remembering, you may return the existing notes \
unchanged. Output ONLY the notes themselves -- no preamble, no headers."""


def _format_transcript(messages: list) -> str:
    """Reduce a message list to just the human-readable back-and-forth --
    customer asks, agent answers -- with tool calls compressed to a short
    note instead of dumped in full. Keeps the summarization prompt focused
    on what a human would actually narrate, not raw tool payloads."""
    lines = []
    for m in messages:
        if isinstance(m, HumanMessage):
            lines.append(f"Customer: {m.content}")
        elif isinstance(m, AIMessage) and m.content:
            lines.append(f"Agent: {m.content}")
        elif isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
            names = ", ".join(c["name"] for c in m.tool_calls)
            lines.append(f"[Agent used tool(s): {names}]")
        # ToolMessage and bare SystemMessage are intentionally skipped --
        # raw DB output isn't what a human summary should read like.
    return "\n".join(lines)


def summarize_and_save(customer_id: int, messages: list) -> str:
    """Condense a finished conversation into updated long-term notes and
    persist them. Returns the new summary so the caller can show it."""
    transcript = _format_transcript(messages)
    if not transcript.strip():
        return get_customer_memory(customer_id)  # nothing happened, nothing to save

    existing_notes = get_customer_memory(customer_id) or "(none yet -- first conversation)"

    llm = ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=0.2)
    prompt = SUMMARY_PROMPT.format(existing_notes=existing_notes, transcript=transcript)
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
    except Exception as e:
        # If the summarization call itself gets rate-limited, don't lose
        # what was already there -- just leave memory as-is and surface
        # the failure instead of silently corrupting good data.
        print(f"  (memory save skipped -- {type(e).__name__}: {e})")
        return existing_notes

    new_summary = response.content.strip()
    update_customer_memory(customer_id, new_summary)
    return new_summary