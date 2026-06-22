const TOOL_LABELS = {
  process_refund: 'a refund',
  cancel_order: 'an order cancellation',
}

// No buttons here anymore -- approving your own refund request was the
// whole problem this phase fixed. This just tells the customer their
// request reached a real person.
export default function ApprovalCard({ tool }) {
  return (
    <div className="approval" role="status">
      <div className="approval__label">Sent for review</div>
      <div className="approval__title">
        A team member is reviewing {TOOL_LABELS[tool] || 'your request'}
      </div>
      <div className="approval__meta">You'll see a reply here once it's resolved.</div>
    </div>
  )
}
