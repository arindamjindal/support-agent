import { useCallback, useEffect, useState } from 'react'
import { getPendingApprovals, decideApproval } from '../api.js'

const TOOL_LABELS = {
  process_refund: 'Refund request',
  cancel_order: 'Cancellation request',
}

function formatArgs(args) {
  return Object.entries(args)
    .filter(([key]) => key !== 'reason')
    .map(([key, value]) => `${key.replace(/_/g, ' ')}: ${value}`)
    .join(' \u00b7 ')
}

export default function StaffDashboard() {
  const [approvals, setApprovals] = useState([])
  const [loading, setLoading] = useState(true)
  const [decidingId, setDecidingId] = useState(null)
  const [error, setError] = useState(null)

  const refresh = useCallback(async () => {
    try {
      const result = await getPendingApprovals()
      setApprovals(result.approvals)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  // Polls instead of pushing -- simplest thing that works for a queue
  // other staff might also be adding to. A real multi-seat product
  // would want a websocket here instead of a 5s poll.
  useEffect(() => {
    refresh()
    const interval = setInterval(refresh, 5000)
    return () => clearInterval(interval)
  }, [refresh])

  async function handleDecide(id, approved) {
    setDecidingId(id)
    try {
      await decideApproval(id, approved)
      await refresh()
    } catch (err) {
      setError(err.message)
    } finally {
      setDecidingId(null)
    }
  }

  return (
    <div className="staff">
      <h1 className="staff__heading">Pending approvals</h1>
      <p className="staff__subhead">
        {loading
          ? 'Loading\u2026'
          : approvals.length === 0
          ? 'Queue is empty \u2014 nothing waiting right now.'
          : `${approvals.length} request${approvals.length === 1 ? '' : 's'} waiting`}
      </p>

      {error && <div className="staff__error">{error}</div>}

      <div className="staff__queue">
        {approvals.map((a) => (
          <div key={a.id} className="staff__card">
            <div className="staff__card-top">
              <span className="staff__card-type">{TOOL_LABELS[a.tool_name] || a.tool_name}</span>
              <span className="staff__card-time">{a.created_at}</span>
            </div>
            <div className="staff__card-customer">
              {a.customer_name} <span className="staff__card-tier">{a.customer_tier}</span>
            </div>
            <div className="staff__card-meta">{formatArgs(a.tool_args)}</div>
            {a.tool_args.reason && (
              <div className="staff__card-reason">&ldquo;{a.tool_args.reason}&rdquo;</div>
            )}

            <div className="staff__card-actions">
              <button
                className="staff__btn staff__btn--decline"
                onClick={() => handleDecide(a.id, false)}
                disabled={decidingId === a.id}
              >
                Decline
              </button>
              <button
                className="staff__btn staff__btn--approve"
                onClick={() => handleDecide(a.id, true)}
                disabled={decidingId === a.id}
              >
                Approve
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
