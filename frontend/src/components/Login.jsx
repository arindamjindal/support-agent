import { useState } from 'react'
import { login, signup } from '../api.js'

export default function Login({ onAuth }) {
  const [mode, setMode] = useState('login') // 'login' | 'signup'
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const result = mode === 'login' ? await login(email, password) : await signup(name, email, password)
      onAuth(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth">
      <form className="auth__card" onSubmit={handleSubmit}>
        <div className="auth__wordmark">Nimbus Gear</div>
        <p className="auth__tag">Support</p>

        <div className="auth__tabs">
          <button
            type="button"
            className={mode === 'login' ? 'auth__tab auth__tab--active' : 'auth__tab'}
            onClick={() => setMode('login')}
          >
            Log in
          </button>
          <button
            type="button"
            className={mode === 'signup' ? 'auth__tab auth__tab--active' : 'auth__tab'}
            onClick={() => setMode('signup')}
          >
            Sign up
          </button>
        </div>

        {mode === 'signup' && (
          <input
            type="text"
            placeholder="Your name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        )}
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={8}
        />

        {error && <div className="auth__error">{error}</div>}

        <button type="submit" className="auth__submit" disabled={busy}>
          {busy ? 'Please wait\u2026' : mode === 'login' ? 'Log in' : 'Create account'}
        </button>

        {mode === 'login' && (
          <p className="auth__hint">
            Test account: any seeded customer&rsquo;s email &middot; password <code>nimbus123</code>
          </p>
        )}
      </form>
    </div>
  )
}
