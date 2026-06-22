import { useEffect, useRef, useState } from 'react'
import MessageBubble from './MessageBubble.jsx'
import ApprovalCard from './ApprovalCard.jsx'

export default function ChatWindow({
  messages,
  pendingReview,
  onSend,
  isStreaming,
  error,
}) {
  const [draft, setDraft] = useState('')
  const scrollRef = useRef(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, pendingReview])

  function handleSubmit(e) {
    e.preventDefault()
    const trimmed = draft.trim()
    if (!trimmed || isStreaming || pendingReview) return
    onSend(trimmed)
    setDraft('')
  }

  return (
    <section className="chat">
      <div className="chat__scroll" ref={scrollRef}>
        {messages.length === 0 && !pendingReview && (
          <div className="chat__empty">
            <p>Ask about an order, a return, or anything else — I&rsquo;ll look up real account details before I answer.</p>
          </div>
        )}

        {messages.map((m, i) => (
          <MessageBubble key={i} role={m.role} content={m.content} />
        ))}

        {pendingReview && <ApprovalCard tool={pendingReview.tool} />}

        {isStreaming && !pendingReview && (
          <div className="bubble bubble--agent bubble--pending">
            <div className="bubble__content bubble__content--typing">
              <span /><span /><span />
            </div>
          </div>
        )}

        {error && (
          <div className="chat__error" role="alert">
            {error}
          </div>
        )}
      </div>

      <form className="chat__input" onSubmit={handleSubmit}>
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={pendingReview ? 'Waiting on a team member\u2026' : 'Type a message'}
          disabled={isStreaming || !!pendingReview}
        />
        <button type="submit" disabled={isStreaming || !!pendingReview || !draft.trim()}>
          Send
        </button>
      </form>
    </section>
  )
}
