import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { api, err, inr, STATUS } from '../api'
import { useApp } from '../App.jsx'

export default function Account() {
  const { setUser, user } = useApp(); const nav = useNavigate()
  const [mode, setMode] = useState('login') // login | signup | verify | otp | otpcode | forgot | reset
  const [f, setF] = useState({ name: '', email: '', phone: '', password: '', code: '' })
  const [msg, setMsg] = useState(''); const [bad, setBad] = useState('')
  useEffect(() => { if (user) nav('/') }, [user])
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const go = (m, text) => { setMode(m); setMsg(text || ''); setBad('') }
  const loggedIn = (r) => { setUser(r.data); nav('/') }
  const run = (fn) => async (e) => { e.preventDefault(); setBad(''); try { await fn() } catch (x) { setBad(err(x)); if (x?.response?.status === 403) go('verify', err(x)) } }
  const E = { email: f.email }

  const submit = {
    login: run(async () => loggedIn(await api.post('/auth/login', { email: f.email, password: f.password }))),
    signup: run(async () => { const r = await api.post('/auth/signup', f); go('verify', r.data.message) }),
    verify: run(async () => loggedIn(await api.post('/auth/verify', { ...E, code: f.code }))),
    otp: run(async () => { const r = await api.post('/auth/otp/request', { phone: f.phone }); go('otpcode', r.data.message) }),
    otpcode: run(async () => loggedIn(await api.post('/auth/otp/login', { phone: f.phone, code: f.code }))),
    forgot: run(async () => { const r = await api.post('/auth/forgot', E); go('reset', r.data.message) }),
    reset: run(async () => { await api.post('/auth/reset', { ...E, code: f.code, password: f.password }); go('login', 'Password updated. Please log in') }),
  }[mode]
  const titles = { login: 'Log in', signup: 'Create account', verify: 'Verify your mobile', otp: 'Log in with OTP', otpcode: 'Enter OTP', forgot: 'Reset password', reset: 'Set a new password' }
  const show = { name: mode === 'signup', phone: ['signup', 'otp', 'otpcode'].includes(mode), email: !['otp', 'otpcode'].includes(mode), password: ['login', 'signup', 'reset'].includes(mode), code: ['verify', 'otpcode', 'reset'].includes(mode) }
  const btn = { login: 'Log in', signup: 'Send OTP', verify: 'Verify and continue', otp: 'Send OTP', otpcode: 'Log in', forgot: 'Send OTP', reset: 'Update password' }[mode]
  return (
    <form onSubmit={submit} style={{ maxWidth: 400, margin: '2.5rem auto' }}>
      <h2>{titles[mode]}</h2>
      {msg && <div className="ok">{msg}</div>}{bad && <div className="err">{bad}</div>}
      {show.name && <><label>Full name</label><input required value={f.name} onChange={set('name')} /></>}
      {show.email && <><label>Email</label><input required type="email" value={f.email} onChange={set('email')} /></>}
      {show.phone && <><label>Mobile number</label><input required pattern="[6-9][0-9]{9}" maxLength="10" value={f.phone} onChange={set('phone')} /></>}
      {show.password && <><label>{mode === 'reset' ? 'New password' : 'Password'} (min 8 characters)</label><input required minLength="8" type="password" value={f.password} onChange={set('password')} /></>}
      {show.code && <><label>6-digit OTP (sent by SMS)</label><input required inputMode="numeric" maxLength="6" value={f.code} onChange={set('code')} autoComplete="one-time-code" /></>}
      <div style={{ margin: '1.2rem 0' }}><button className="btn">{btn}</button></div>
      {mode === 'login' && <p><a href="#" onClick={(e) => { e.preventDefault(); go('otp') }}>Log in with OTP</a> | <a href="#" onClick={(e) => { e.preventDefault(); go('forgot') }}>Forgot password</a></p>}
      <p>{mode === 'signup' ? <>Already have an account? <a href="#" onClick={(e) => { e.preventDefault(); go('login') }}>Log in</a></>
        : mode === 'login' ? <>New here? <a href="#" onClick={(e) => { e.preventDefault(); go('signup') }}>Create an account</a></>
        : <a href="#" onClick={(e) => { e.preventDefault(); go('login') }}>Back to log in</a>}</p>
    </form>)
}

const FLOW = ['PLACED', 'CONFIRMED', 'PACKED', 'SHIPPED', 'OUT_FOR_DELIVERY', 'DELIVERED']
export function Orders() {
  const [orders, setOrders] = useState(null); const { state } = useLocation()
  useEffect(() => { api.get('/orders/my').then((r) => setOrders(r.data)) }, [])
  if (!orders) return null
  return (<div style={{ maxWidth: 720, margin: '2rem auto' }}>
    <h2>My orders</h2>
    {state?.placed && (state.pending ? <div className="ok">We received your payment details for order #{state.placed}. It will be placed as soon as we confirm the payment.</div> : <div className="ok">Thank you! Order #{state.placed} is placed. We will pack it soon.</div>)}
    {!orders.length && <div className="empty">You have not placed any orders yet.</div>}
    {orders.map((o) => (<div className="box" key={o.id}>
      <div className="row"><strong>Order #{o.id}</strong><span className="badge">{STATUS[o.order_status]}</span></div>
      <small>{new Date(o.created_at).toLocaleString('en-IN')}</small>
      {o.items.map((i, k) => <div key={k}>{i.name}, age {i.size_label} x {i.qty}</div>)}
      <div className="line" /><div className="row"><span>{o.payment_status === 'PAID' ? 'Paid via UPI' : 'UPI payment is being verified'}</span><strong>{inr(o.total)}</strong></div>
      {o.tracking_no && <p>Shipped with {o.courier}. Tracking no. <strong>{o.tracking_no}</strong></p>}
      <ul className="tl">{o.history.filter((h) => h.status !== 'PENDING_PAYMENT').map((h, k) => (
        <li key={k}>{STATUS[h.status]}<small>{new Date(h.at).toLocaleString('en-IN')}{h.note ? ` | ${h.note}` : ''}</small></li>))}</ul>
    </div>))}
  </div>)
}
