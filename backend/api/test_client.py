"""
Drives the FastAPI backend over real HTTP, the same way the future React
frontend will. Useful for testing the API contract before Phase 7 exists.

Run the server first, in a separate terminal:
    cd backend/api
    uvicorn main:app --reload --port 8000

Then run this:
    python test_client.py
"""

import json
import requests

BASE_URL = "http://localhost:8000"


def stream_events(response):
    """Parse our hand-rolled SSE format back out of a streaming response."""
    event_type = None
    for line in response.iter_lines(decode_unicode=True):
        if line is None or line == "":
            continue
        if line.startswith("event:"):
            event_type = line.removeprefix("event:").strip()
        elif line.startswith("data:"):
            data = json.loads(line.removeprefix("data:").strip())
            yield event_type, data


def send_message(customer_id: int, message: str):
    resp = requests.post(
        f"{BASE_URL}/chat/stream",
        json={"customer_id": customer_id, "message": message},
        stream=True,
    )
    handle_events(customer_id, resp)


def resume(customer_id: int, approved: bool):
    resp = requests.post(
        f"{BASE_URL}/chat/resume",
        json={"customer_id": customer_id, "approved": approved},
        stream=True,
    )
    handle_events(customer_id, resp)


def handle_events(customer_id: int, resp):
    for event_type, data in stream_events(resp):
        if event_type == "tool_call":
            print(f"  \U0001f50d calling {data['tool']}({data['args']})")
        elif event_type == "tool_result":
            print(f"  \u2192 {data['content'][:100]}")
        elif event_type == "final":
            print(f"Agent: {data['content']}\n")
        elif event_type == "approval_required":
            print(f"\n  [APPROVAL NEEDED] {data['tool']}({data['args']})")
            answer = input("  Approve? (y/n): ").strip().lower()
            resume(customer_id, answer in ("y", "yes"))


def main():
    raw = input("Customer ID (default 7): ").strip()
    customer_id = int(raw) if raw else 7

    print(f"\nChatting as customer_id={customer_id} via the API. Type 'quit' to exit.\n")
    while True:
        msg = input("You: ").strip()
        if msg.lower() in ("quit", "exit"):
            break
        if not msg:
            continue
        send_message(customer_id, msg)

    print("\nEnding session...")
    r = requests.post(f"{BASE_URL}/chat/end", json={"customer_id": customer_id})
    print("Saved memory:", r.json()["summary"])


if __name__ == "__main__":
    main()