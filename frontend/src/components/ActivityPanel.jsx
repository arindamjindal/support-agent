const TOOL_VERBS = {
  lookup_orders: 'Looking up orders',
  search_kb: 'Searching the knowledge base',
  create_ticket: 'Opening a ticket',
  escalate: 'Escalating to a human agent',
  get_customer_history: 'Pulling up customer history',
  process_refund: 'Processing a refund',
  cancel_order: 'Cancelling an order',
}

export default function ActivityPanel({ items, isWorking }) {
  return (
    <aside className="activity">
      <div className="activity__header">
        <span className={`activity__orb${isWorking ? ' activity__orb--active' : ''}`} aria-hidden="true" />
        <span>Agent activity</span>
      </div>

      {items.length === 0 ? (
        <p className="activity__empty">Nothing yet — actions the agent takes will show up here as they happen.</p>
      ) : (
        <ol className="activity__list">
          {items.map((item) => (
            <li key={item.id} className={`activity__item activity__item--${item.kind}`}>
              {item.kind === 'call' ? (
                <span className="activity__text">{TOOL_VERBS[item.tool] || item.tool}&hellip;</span>
              ) : (
                <span className="activity__text activity__text--result">{item.content}</span>
              )}
            </li>
          ))}
        </ol>
      )}
    </aside>
  )
}
