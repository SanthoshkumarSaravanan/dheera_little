import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { QRCodeSVG } from 'qrcode.react'
import { api, err, inr } from '../api'
import { useApp } from '../App.jsx'

const STATES = ['Andhra Pradesh','Arunachal Pradesh','Assam','Bihar','Chhattisgarh','Goa','Gujarat','Haryana','Himachal Pradesh','Jharkhand','Karnataka','Kerala','Madhya Pradesh','Maharashtra','Manipur','Meghalaya','Mizoram','Nagaland','Odisha','Punjab','Rajasthan','Sikkim','Tamil Nadu','Telangana','Tripura','Uttar Pradesh','Uttarakhand','West Bengal','Andaman and Nicobar Islands','Chandigarh','Dadra and Nagar Haveli and Daman and Diu','Delhi','Jammu and Kashmir','Ladakh','Lakshadweep','Puducherry']

function loadRzp() {
  return new Promise((ok, no) => {
    if (window.Razorpay) return ok()
    const s = document.createElement('script'); s.src = 'https://checkout.razorpay.com/v1/checkout.js'
    s.onload = ok; s.onerror = () => no(new Error('Could not load payment window')); document.body.appendChild(s)
  })
}

export default function Cart() {
  const { cart, setCart, user } = useApp(); const nav = useNavigate()
  const [cfg, setCfg] = useState({ shipping_flat: 60, free_above: 999 })
  const [a, setA] = useState({ name: user?.name || '', phone: '', line1: '', line2: '', city: '', state: 'Tamil Nadu', pincode: '' })
  const [msg, setMsg] = useState(''); const [busy, setBusy] = useState(false)
  const [upi, setUpi] = useState(null); const [utr, setUtr] = useState('')
  useEffect(() => { api.get('/config').then((r) => setCfg(r.data)) }, [])
  const subtotal = cart.reduce((t, i) => t + i.price * i.qty, 0)
  const ship = subtotal === 0 || subtotal >= cfg.free_above ? 0 : cfg.shipping_flat
  const set = (k) => (e) => setA({ ...a, [k]: e.target.value })
  const qty = (i, d) => setCart(cart.map((c) => c === i ? { ...c, qty: Math.max(1, Math.min(10, c.qty + d)) } : c))
  const done = (o) => { setCart([]); nav('/orders', { state: { placed: o.id } }) }

  const pay = async (e) => {
    e.preventDefault(); setMsg('')
    if (!user) return nav('/account')
    setBusy(true)
    try {
      const { data } = await api.post('/orders', { items: cart.map(({ product_id, size_id, qty }) => ({ product_id, size_id, qty })), address: a })
      if (data.mode === 'upi') { setUpi(data); setBusy(false); return }  // pay to our UPI ID, then enter UTR
      if (data.mode === 'dev') {  // test mode: nothing configured
        const r = await api.post(`/payments/dev-confirm/${data.order_id}`); return done(r.data)
      }
      await loadRzp()
      new window.Razorpay({
        key: data.key_id, order_id: data.rzp_order_id, amount: data.amount * 100, currency: 'INR', name: 'Dheera Littles',
        description: `Order #${data.order_id}`, prefill: { name: a.name, contact: a.phone, email: user.email }, theme: { color: '#66765f' },
        config: { display: { blocks: { upi: { name: 'Pay with UPI', instruments: [{ method: 'upi' }] } }, sequence: ['block.upi'], preferences: { show_default_blocks: false } } },
        handler: async (r) => {
          try { const v = await api.post('/payments/verify', { order_id: data.order_id, ...r }); done(v.data) }
          catch (x) { setMsg(err(x)); setBusy(false) }
        },
        modal: { ondismiss: () => setBusy(false) },
      }).open()
    } catch (x) { setMsg(err(x)); setBusy(false) }
  }

  const submitUtr = async (e) => {
    e.preventDefault(); setMsg(''); setBusy(true)
    try { await api.post('/payments/upi-submit', { order_id: upi.order_id, utr }); setCart([]); nav('/orders', { state: { placed: upi.order_id, pending: true } }) }
    catch (x) { setMsg(err(x)); setBusy(false) }
  }

  if (!cart.length) return <div className="empty"><h2>Your bag is empty</h2><Link className="btn" to="/">Browse dresses</Link></div>
  return (
    <div className="cols">
      <div>
        <h2>Your bag</h2>
        {cart.map((i) => (
          <div className="box row" key={i.product_id + '-' + i.size_id}>
            <div className="row" style={{ justifyContent: 'flex-start' }}>
              {i.image && <img src={i.image} alt="" width="56" height="70" style={{ objectFit: 'cover', borderRadius: 3 }} />}
              <div>{i.name}<br /><small>Age {i.size_label}</small><br />{inr(i.price)}</div>
            </div>
            <div className="row">
              <button className="chip" onClick={() => qty(i, -1)}>-</button>{i.qty}<button className="chip" onClick={() => qty(i, 1)}>+</button>
              <button className="btn ghost sm" onClick={() => setCart(cart.filter((c) => c !== i))}>Remove</button>
            </div>
          </div>))}
        <div className="box">
          <div className="row"><span>Subtotal</span><span>{inr(subtotal)}</span></div>
          <div className="row"><span>Shipping</span><span>{ship ? inr(ship) : 'Free'}</span></div>
          <div className="line" />
          <div className="row"><strong>Total</strong><strong>{inr(subtotal + ship)}</strong></div>
          {ship > 0 && <small>Free shipping on orders above {inr(cfg.free_above)}</small>}
        </div>
      </div>
      {upi ? <div>
        <h2>Pay with UPI</h2>
        <div className="box" style={{ textAlign: 'center' }}>
          <QRCodeSVG value={upi.upi_link} size={200} />
          <p>Scan with GPay, PhonePe, Paytm or any UPI app</p>
          <p>Pay exactly <strong>{inr(upi.amount)}</strong> to <strong>{upi.upi_id}</strong></p>
          <a className="btn ghost sm" href={upi.upi_link}>Open UPI app on this phone</a>
        </div>
        <form onSubmit={submitUtr}>
          <label>After paying, enter the 12-digit UTR / reference number shown in your UPI app</label>
          <input required inputMode="numeric" pattern="[0-9]{12}" maxLength="12" value={utr} onChange={(e) => setUtr(e.target.value.replace(/\D/g, ''))} />
          {msg && <div className="err">{msg}</div>}
          <div style={{ marginTop: '1.2rem' }}><button className="btn" disabled={busy || utr.length !== 12}>{busy ? 'Please wait' : 'I have paid'}</button></div>
          <small>Your order is placed once we confirm the payment in our account.</small>
        </form>
      </div> :
      <form onSubmit={pay}>
        <h2>Delivery address</h2>
        <label>Full name</label><input required value={a.name} onChange={set('name')} />
        <label>Mobile number</label><input required inputMode="numeric" pattern="[6-9][0-9]{9}" maxLength="10" value={a.phone} onChange={set('phone')} />
        <label>Address line 1</label><input required value={a.line1} onChange={set('line1')} />
        <label>Address line 2 (optional)</label><input value={a.line2} onChange={set('line2')} />
        <div className="two">
          <div><label>City</label><input required value={a.city} onChange={set('city')} /></div>
          <div><label>Pincode</label><input required inputMode="numeric" pattern="[1-9][0-9]{5}" maxLength="6" value={a.pincode} onChange={set('pincode')} /></div>
        </div>
        <label>State</label><select value={a.state} onChange={set('state')}>{STATES.map((s) => <option key={s}>{s}</option>)}</select>
        {msg && <div className="err">{msg}</div>}
        {!user && <div className="err">Please <Link to="/account">log in</Link> to place your order.</div>}
        <div style={{ marginTop: '1.4rem' }}><button className="btn" disabled={busy || !user}>{busy ? 'Please wait' : `Pay ${inr(subtotal + ship)} with UPI`}</button></div>
        <small>Pay with GPay, PhonePe, Paytm or any UPI app.</small>
      </form>}
    </div>)
}
