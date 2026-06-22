// Talks to the FastAPI backend from Phase 6. The backend doesn't use the
// browser's built-in EventSource (that only supports GET requests, and we
// need to POST a customer_id + message) -- instead it streams plain SSE-
// formatted text over a regular fetch(), which we parse by hand below.

const BASE_URL = import.meta.env.VITE_API_URL || 'https://support-agent-backend-25lb.onrender.com'

function authHeaders() {
  const token = localStorage.getItem('nimbus_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function parseJsonError(res) {
  const body = await res.json().catch(() => ({}))
  return body.detail || `Request failed (${res.status})`
}

export async function login(email, password) {
  const res = await fetch(`${BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) throw new Error(await parseJsonError(res))
  return res.json()
}

export async function signup(name, email, password) {
  const res = await fetch(`${BASE_URL}/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, password }),
  })
  if (!res.ok) throw new Error(await parseJsonError(res))
  return res.json()
}

async function* parseSSE(response) {
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let eventType = null

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    const lines = buffer.split('\n')
    buffer = lines.pop() // last entry may be a partial line -- keep it for next read

    for (const line of lines) {
      if (line.startsWith('event:')) {
        eventType = line.slice(6).trim()
      } else if (line.startsWith('data:')) {
        const data = JSON.parse(line.slice(5).trim())
        yield { type: eventType, data }
      }
    }
  }
}

export async function sendMessage(message) {
  const res = await fetch(`${BASE_URL}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ message }),
  })
  if (!res.ok) throw new Error(`Server responded with ${res.status}`)
  return parseSSE(res)
}

export async function getChatHistory() {
  const res = await fetch(`${BASE_URL}/chat/history`, {
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error(`Server responded with ${res.status}`)
  return res.json()
}

export async function endSession() {
  const res = await fetch(`${BASE_URL}/chat/end`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
  })
  return res.json()
}

// ---------------------------------------------------------------------
// Staff
// ---------------------------------------------------------------------

export async function getPendingApprovals() {
  const res = await fetch(`${BASE_URL}/staff/pending-approvals`, {
    headers: authHeaders(),
  })
  if (!res.ok) throw new Error(`Server responded with ${res.status}`)
  return res.json()
}

export async function decideApproval(approvalId, approved) {
  const res = await fetch(`${BASE_URL}/staff/approvals/${approvalId}/decide`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ approved }),
  })
  if (!res.ok) throw new Error(await parseJsonError(res))
  return res.json()
}