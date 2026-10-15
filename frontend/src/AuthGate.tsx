import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { ArrowRight, KeyRound, LoaderCircle, LockKeyhole, LogIn, Mail, Radar, ShieldCheck } from 'lucide-react'
import type { Session } from '@supabase/supabase-js'
import { supabase } from './lib/supabase'

type Mode = 'login' | 'signup' | 'reset' | 'update'

export default function AuthGate({ children }: { children: (session: Session) => ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [initializing, setInitializing] = useState(true)
  const [mode, setMode] = useState<Mode>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [working, setWorking] = useState(false)

  useEffect(() => {
    if (!supabase) { setInitializing(false); return }
    // onAuthStateChange provides INITIAL_SESSION and later refresh events.
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, nextSession) => {
      setSession(nextSession)
      if (event === 'PASSWORD_RECOVERY') setMode('update')
      if (event === 'SIGNED_OUT') { setPassword(''); setConfirm('') }
      setInitializing(false)
    })
    return () => subscription.unsubscribe()
  }, [])

  const changeMode = (next: Mode) => { setMode(next); setMessage(''); setError(''); setPassword(''); setConfirm('') }
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!supabase) return
    setError(''); setMessage(''); setWorking(true)
    try {
      if (mode === 'login') {
        const { error: err } = await supabase.auth.signInWithPassword({ email: email.trim(), password })
        if (err) throw err
      } else if (mode === 'signup') {
        if (password.length < 8) throw new Error('Use a password of at least 8 characters.')
        if (password !== confirm) throw new Error('Passwords do not match.')
        const { data, error: err } = await supabase.auth.signUp({
          email: email.trim(), password,
          options: { emailRedirectTo: window.location.origin },
        })
        if (err) throw err
        if (!data.session) setMessage('Check your email to confirm your account, then sign in.')
      } else if (mode === 'reset') {
        const { error: err } = await supabase.auth.resetPasswordForEmail(email.trim(), { redirectTo: window.location.origin })
        if (err) throw err
        setMessage('If the account exists, a password reset email will arrive shortly.')
      } else {
        if (password.length < 8) throw new Error('Use a password of at least 8 characters.')
        if (password !== confirm) throw new Error('Passwords do not match.')
        const { error: err } = await supabase.auth.updateUser({ password })
        if (err) throw err
        setMessage('Password updated. Your workspace is ready.')
        setMode('login')
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Authentication failed.')
    } finally { setWorking(false) }
  }

  if (!supabase) return <div className="auth-screen"><section className="auth-card"><Radar size={36}/><h1>Connect Supabase</h1><p>Copy <code>frontend/.env.example</code> to <code>frontend/.env.local</code> and set your project URL and publishable key, then restart Vite.</p><p>See <code>README_PHASE4.md</code> for setup. There is no insecure guest mode.</p></section></div>
  if (initializing) return <div className="auth-screen"><div className="auth-wait"><LoaderCircle className="spin" size={25}/> Checking your session…</div></div>
  if (session && mode !== 'update') return <>{children(session)}</>

  return <div className="auth-screen"><section className="auth-card" aria-label="Account access">
    <div className="auth-logo"><span><Radar size={24}/></span><strong>lead<span>scraper</span></strong></div>
    <div className="auth-overline"><ShieldCheck size={15}/> YOUR PRIVATE WORKSPACE</div>
    <h1>{mode === 'login' ? 'Welcome back.' : mode === 'signup' ? 'Create an account.' : mode === 'reset' ? 'Reset your password.' : 'Choose a new password.'}</h1>
    <p className="auth-intro">{mode === 'login' ? 'Sign in to access your jobs and lead records.' : mode === 'signup' ? 'Your searches and imports stay in your account.' : mode === 'reset' ? 'We will send password-reset instructions to your email.' : 'Enter your new account password below.'}</p>
    <form onSubmit={e => void submit(e)}>
      {mode !== 'update' && <label>Email address<div className="auth-field"><Mail size={18}/><input type="email" autoComplete="email" required placeholder="you@company.com" value={email} onChange={e => setEmail(e.target.value)} /></div></label>}
      {(mode === 'login' || mode === 'signup' || mode === 'update') && <label>Password<div className="auth-field"><LockKeyhole size={18}/><input type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} required minLength={mode === 'login' ? 1 : 8} placeholder="Your password" value={password} onChange={e => setPassword(e.target.value)} /></div></label>}
      {(mode === 'signup' || mode === 'update') && <label>Confirm password<div className="auth-field"><KeyRound size={18}/><input type="password" autoComplete="new-password" required minLength={8} placeholder="Confirm password" value={confirm} onChange={e => setConfirm(e.target.value)} /></div></label>}
      {error && <div className="auth-notice error" role="alert">{error}</div>}
      {message && <div className="auth-notice success" role="status">{message}</div>}
      <button className="auth-submit" type="submit" disabled={working}>{working ? <LoaderCircle size={18} className="spin"/> : mode === 'login' ? <LogIn size={18}/> : <ArrowRight size={18}/>} {working ? 'Please wait…' : mode === 'login' ? 'Sign in' : mode === 'signup' ? 'Create account' : mode === 'reset' ? 'Send reset email' : 'Update password'}</button>
    </form>
    <div className="auth-links">{mode === 'login' ? <><button onClick={() => changeMode('reset')}>Forgot password?</button><button onClick={() => changeMode('signup')}>Create account</button></> : <button onClick={() => changeMode('login')}>Return to sign in</button>}</div>
    <div className="auth-footnote"><ShieldCheck size={16}/> Account sessions are verified by the Python API before accessing private data.</div>
  </section></div>
}
