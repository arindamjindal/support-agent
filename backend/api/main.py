"""
FastAPI layer over the agent graph.

Customer endpoints:  POST /auth/signup, POST /auth/login, POST /chat/stream,
                      GET /chat/history, POST /chat/end
Staff endpoints:      GET /staff/pending-approvals, POST /staff/approvals/{id}/decide

The key change from the pre-staff-view version: a customer's chat no
longer has a /chat/resume endpoint at all. When the agent proposes a
refund or cancellation, the graph still pauses on interrupt() exactly
as before -- but now that pause gets recorded as a row in
pending_approvals, and the ONLY way to unblock it is a staff member
deciding on it through the staff endpoint. The customer sees "sent for
review," not a button that resolves their own request.
"""

import json
import sys
from pathlib import Path
from typing import Optional

sys.path.append(str(Path(__file__).resolve().parent.parent / "agent"))
sys.path.append(str(Path(__file__).resolve().parent.parent / "auth"))
sys.path.append(str(Path(__file__).resolve().parent.parent / "staff"))

from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.types import Command
import jwt

from graph import build_graph
from memory import summarize_and_save
from security import hash_password, verify_password, create_access_token, decode_access_token
from db import get_user_by_email, get_user_by_id, create_customer_and_user, get_customer
from approvals import (
    create_pending_approval as staff_create_pending_approval,
    list_pending_approvals,
    get_pending_approval,
    resolve_pending_approval,
)

app = FastAPI(title="Nimbus Gear Support Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

agent_app = build_graph()


# ---------------------------------------------------------------------------
# Auth dependencies
# ---------------------------------------------------------------------------

def get_current_user(authorization: str = Header(None)) -> dict:
    """Decodes the token into {user_id, role, customer_id}. Every other
    auth dependency builds on this one."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        return decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired, please log in again")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid session")


def require_customer(user: dict = Depends(get_current_user)) -> int:
    """Used by every /chat/* endpoint. Returns the verified customer_id
    -- a staff token has none, so it's rejected here, not trusted from
    anything the client sends."""
    if user["role"] != "customer" or user["customer_id"] is None:
        raise HTTPException(status_code=403, detail="Customer access required")
    return user["customer_id"]


def require_staff(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "staff":
        raise HTTPException(status_code=403, detail="Staff access required")
    return user


# ---------------------------------------------------------------------------
# Request/response models
# ---------------------------------------------------------------------------

class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    customer_id: Optional[int]
    name: str
    role: str


class ChatRequest(BaseModel):
    message: str


class ApprovalDecision(BaseModel):
    approved: bool


# ---------------------------------------------------------------------------
# Streaming helpers
# ---------------------------------------------------------------------------

def thread_config(customer_id: int) -> dict:
    return {"configurable": {"thread_id": f"customer-{customer_id}-web-session"}}


def format_sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def process_stream(stream_iter, customer_id: Optional[int] = None):
    """Translates raw LangGraph stream chunks into SSE events. When a
    customer's stream hits an interrupt, this is also where the
    pending_approvals row gets created -- the one moment the customer
    facing flow and the staff queue connect."""
    for chunk in stream_iter:
        if "__interrupt__" in chunk:
            payload = chunk["__interrupt__"][0].value
            if customer_id is not None:
                staff_create_pending_approval(customer_id, payload["tool"], payload["args"])
            yield format_sse("pending_review", {"tool": payload["tool"]})
            return

        for _node_name, node_output in chunk.items():
            for m in node_output.get("messages", []):
                if isinstance(m, AIMessage):
                    if getattr(m, "tool_calls", None):
                        for call in m.tool_calls:
                            yield format_sse("tool_call", {"tool": call["name"], "args": call["args"]})
                    elif m.content:
                        yield format_sse("final", {"content": m.content})
                elif isinstance(m, ToolMessage):
                    yield format_sse("tool_result", {"content": m.content})


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.post("/auth/signup", response_model=AuthResponse)
def signup(req: SignupRequest):
    if get_user_by_email(req.email):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    user = create_customer_and_user(req.name, req.email, hash_password(req.password))
    customer = get_customer(user.customer_id)
    token = create_access_token(user.id, "customer", user.customer_id)
    return AuthResponse(access_token=token, customer_id=user.customer_id, name=customer.name, role="customer")


@app.post("/auth/login", response_model=AuthResponse)
def login(req: LoginRequest):
    user = get_user_by_email(req.email)
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    token = create_access_token(user.id, user.role, user.customer_id)
    if user.role == "staff":
        name = "Support staff"
    else:
        name = get_customer(user.customer_id).name
    return AuthResponse(access_token=token, customer_id=user.customer_id, name=name, role=user.role)


# ---------------------------------------------------------------------------
# Customer chat
# ---------------------------------------------------------------------------

@app.post("/chat/stream")
async def chat_stream(req: ChatRequest, customer_id: int = Depends(require_customer)):
    config = thread_config(customer_id)
    payload = {"messages": [HumanMessage(content=req.message)], "customer_id": customer_id}
    return StreamingResponse(
        process_stream(agent_app.stream(payload, config=config, stream_mode="updates"), customer_id=customer_id),
        media_type="text/event-stream",
    )


@app.get("/chat/history")
def chat_history(customer_id: int = Depends(require_customer)):
    """So reloading the page (or coming back after staff resolves a
    request) doesn't lose the conversation -- the frontend never kept
    its own copy, the checkpointer always had the real one."""
    state = agent_app.get_state(thread_config(customer_id))
    messages = state.values.get("messages", []) if state.values else []
    history = []
    for m in messages:
        if isinstance(m, HumanMessage):
            history.append({"role": "customer", "content": m.content})
        elif isinstance(m, AIMessage) and m.content:
            history.append({"role": "agent", "content": m.content})
    return {"messages": history}


@app.post("/chat/end")
async def chat_end(customer_id: int = Depends(require_customer)):
    state = agent_app.get_state(thread_config(customer_id))
    messages = state.values.get("messages", []) if state.values else []
    summary = summarize_and_save(customer_id, messages)
    return {"summary": summary}


# ---------------------------------------------------------------------------
# Staff
# ---------------------------------------------------------------------------

@app.get("/staff/pending-approvals")
def staff_pending_approvals(staff_user: dict = Depends(require_staff)):
    return {"approvals": list_pending_approvals()}


@app.post("/staff/approvals/{approval_id}/decide")
def staff_decide(approval_id: int, decision: ApprovalDecision, staff_user: dict = Depends(require_staff)):
    approval = get_pending_approval(approval_id)
    if not approval or approval["status"] != "pending":
        raise HTTPException(status_code=404, detail="No pending approval with that ID")

    config = thread_config(approval["customer_id"])
    agent_reply = None
    for chunk in agent_app.stream(Command(resume=decision.approved), config=config, stream_mode="updates"):
        for _node, output in chunk.items():
            for m in output.get("messages", []):
                if isinstance(m, AIMessage) and m.content:
                    agent_reply = m.content

    staff_record = get_user_by_id(staff_user["user_id"])
    resolve_pending_approval(approval_id, decision.approved, staff_record.email if staff_record else "staff")

    return {"resolved": True, "approved": decision.approved, "agent_reply": agent_reply}