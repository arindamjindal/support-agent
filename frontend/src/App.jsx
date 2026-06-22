import { useEffect, useState } from 'react'
import Login from './components/Login.jsx'
import Header from './components/Header.jsx'
import ChatWindow from './components/ChatWindow.jsx'
import ActivityPanel from './components/ActivityPanel.jsx'
import StaffDashboard from './components/StaffDashboard.jsx'
import { sendMessage, getChatHistory, endSession } from './api.js'

let idCounter = 0
const nextId = () => `${Date.now()}-${idCounter++}`

export default function App() {
  const [user, setUser] = useState(null)
  const [messages, setMessages] = useState([])
  const [activity, setActivity] = useState([])
  const [pendingReview, setPendingReview] = useState(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState(null)

  // Restore session from localStorage on page load
  useEffect(() => {
    const token = localStorage.getItem('nimbus_token')
    const name = localStorage.getItem('nimbus_name')
    const customerId = localStorage.getItem('nimbus_customer_id')
    const role = localStorage.getItem('nimbus_role')
    if (token && name) {
      setUser({ name, role, customer_id: customerId ? Number(customerId) : null })
    }
  }, [])

  // Load chat history when a customer logs in -- so a page refresh
  // doesn't wipe the conversation, which was the gap this phase fixed.
  useEffect(() => {
    if (!user || user.role !== 'customer') return
    getChatHistory().then((result) => {
      if (result.messages?.length > 0) {
        setMessages(result.messages)
      }
      if (result.pending_review) {
        setPendingReview(result.pending_review)
      }
    }).catch(() => {}) // silently ignore if history isn't there yet
  }, [user])

  function handleAuth(result) {
    localStorage.setItem('nimbus_token', result.access_token)
    localStorage.setItem('nimbus_name', result.name)
    localStorage.setItem('nimbus_role', result.role)
    if (result.customer_id) {
      localStorage.setItem('nimbus_customer_id', result.customer_id)
    }
    setUser({ name: result.name, role: result.role, customer_id: result.customer_id })
  }

  function handleLogout() {
    localStorage.clear()
    setUser(null)
    setMessages([])
    setActivity([])
    setPendingReview(null)
    setSummary(null)
    setError(null)
  }

  async function consume(streamPromise) {
    const stream = await streamPromise
    for await (const { type, data } of stream) {
      if (type === 'tool_call') {
        setActivity((a) => [...a, { id: nextId(), kind: 'call', tool: data.tool }])
      } else if (type === 'tool_result') {
        setActivity((a) => [...a, { id: nextId(), kind: 'result', content: data.content }])
      } else if (type === 'final') {
        setMessages((m) => [...m, { role: 'agent', content: data.content }])
      } else if (type === 'pending_review') {
        setPendingReview({ tool: data.tool })
      }
    }
  }

  async function handleSend(text) {
    setError(null)
    setMessages((m) => [...m, { role: 'customer', content: text }])
    setIsStreaming(true)
    try {
      await consume(sendMessage(text))
    } catch (err) {
      setError(`Couldn't reach the agent (${err.message}).`)
    } finally {
      setIsStreaming(false)
    }
  }

  async function handleEndSession() {
    const result = await endSession()
    setSummary(result.summary)
  }

  if (!user) return <Login onAuth={handleAuth} />

  // Staff see the queue dashboard, nothing else
  if (user.role === 'staff') {
    return (
      <div className="app">
        <Header user={user} onLogout={handleLogout} sessionState="idle" />
        <main className="app__main">
          <StaffDashboard />
        </main>
      </div>
    )
  }

  // Customers see the chat
  const sessionState = pendingReview ? 'waiting' : isStreaming ? 'working' : 'idle'

  return (
    <div className="app">
      <Header user={user} onLogout={handleLogout} sessionState={sessionState} />
      <main className="app__main">
        <ChatWindow
          messages={messages}
          pendingReview={pendingReview}
          onSend={handleSend}
          isStreaming={isStreaming}
          error={error}
        />
        <ActivityPanel items={activity} isWorking={isStreaming} />
      </main>
      <footer className="app__footer">
        <button className="app__end-btn" onClick={handleEndSession}>
          End session &amp; save memory
        </button>
        {summary && (
          <div className="app__summary">
            <strong>Saved to long-term memory:</strong> {summary}
          </div>
        )}
      </footer>
    </div>
  )
}
