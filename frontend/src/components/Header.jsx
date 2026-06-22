export default function Header({ user, onLogout, sessionState }) {
  return (
    <header className="header">
      <div className="header__brand">
        <span className="header__orb" data-state={sessionState} aria-hidden="true" />
        <span className="header__wordmark">Nimbus Gear</span>
        <span className="header__tag">Support</span>
      </div>

      <div className="header__user">
        <span className="header__username">{user.name}</span>
        <button className="header__logout" onClick={onLogout}>
          Log out
        </button>
      </div>
    </header>
  )
}
