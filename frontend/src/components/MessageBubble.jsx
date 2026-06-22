export default function MessageBubble({ role, content }) {
  return (
    <div className={`bubble bubble--${role}`}>
      <div className="bubble__content">{content}</div>
    </div>
  )
}
