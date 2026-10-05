import { useEffect, useState } from 'react'
import { api, err, inr, STATUS } from '../api'

const NEXT = ['PLACED', 'CONFIRMED', 'PACKED', 'SHIPPED', 'OUT_FOR_DELIVERY', 'DELIVERED', 'CANCELLED']

export default function Admin() {
  const [tab, setTab] = useState('orders')
  return (<div>
    <div className="tabs">
      <button className={'chip' + (tab === 'payments' ? ' on' : '')} onClick={() => setTab('payments')}>Payments to verify</button>
      <button className={'chip' + (tab === 'orders' ? ' on' : '')} onClick={() => setTab('orders')}>Orders</button>
      <button className={'chip' + (tab === 'products' ? ' on' : '')} onClick={() => setTab('products')}>Products</button>
    </div>
    {tab === 'payments' ? <PaymentsTab /> : tab === 'orders' ? <OrdersTab /> : <ProductsTab />}
  </div>)
}

function PaymentsTab() {
  const [list, setList] = useState(null); const [m, setM] = useState('')
  const load = () => api.get('/admin/payments/pending').then((r) => setList(r.data))
  useEffect(() => { load() }, [])
  const act = async (id, a) => {
    if (!window.confirm(a === 'confirm' ? 'Did you receive this payment in your UPI app or bank?' : 'Reject this payment and cancel the order?')) return
    try { await api.post(`/admin/payments/${id}/${a}`); setM(a === 'confirm' ? `Order #${id} confirmed and placed` : `Order #${id} rejected`); load() } catch (e) { setM(err(e)) }
  }
  return (<div>
    <h2>Payments to verify</h2>
    <p>Match the amount and UTR with your UPI app or bank statement, then confirm. The order is placed only after you confirm.</p>
    {m && <div className="ok">{m}</div>}
    {list && !list.length && <div className="empty">No payments waiting for verification.</div>}
    {list?.map((o) => (<div className="box" key={o.id}>
      <div className="row"><strong>Order #{o.id} | {inr(o.total)}</strong><span className="badge">UTR {o.utr}</span></div>
      <small>{o.address.name} | {o.customer.email} | {new Date(o.created_at).toLocaleString('en-IN')}</small>
      {o.items.map((i, k) => <div key={k}>{i.name}, age {i.size_label} x {i.qty}</div>)}
      <div style={{ marginTop: '.8rem' }}>
        <button className="btn sm" onClick={() => act(o.id, 'confirm')}>Payment received, confirm</button>{' '}
        <button className="btn ghost sm" onClick={() => act(o.id, 'reject')}>Not received, reject</button>
      </div>
    </div>))}
  </div>)
}

function OrderRow({ o, reload }) {
  const [s, setS] = useState(o.order_status); const [c, setC] = useState(o.courier || ''); const [t, setT] = useState(o.tracking_no || '')
  const [m, setM] = useState('')
  const save = async () => { try { await api.patch(`/admin/orders/${o.id}`, { order_status: s, courier: c, tracking_no: t }); setM('Saved'); reload() } catch (e) { setM(err(e)) } }
  const a = o.address
  return (<div className="box">
    <div className="row"><strong>#{o.id} | {a.name} | {inr(o.total)}</strong><span className="badge">{STATUS[o.order_status]}</span></div>
    <small>{new Date(o.created_at).toLocaleString('en-IN')} | {o.customer.email} | {a.phone}</small>
    <p>{a.line1} {a.line2}, {a.city}, {a.state} - {a.pincode}</p>
    {o.items.map((i, k) => <div key={k}>{i.name}, age {i.size_label} x {i.qty}</div>)}
    <div className="two" style={{ marginTop: '.8rem' }}>
      <div><label>Status</label><select value={s} onChange={(e) => setS(e.target.value)}>{NEXT.map((x) => <option key={x} value={x}>{STATUS[x]}</option>)}</select></div>
      <div><label>Courier</label><input value={c} onChange={(e) => setC(e.target.value)} /></div>
    </div>
    <label>Tracking number</label><input value={t} onChange={(e) => setT(e.target.value)} />
    <div style={{ marginTop: '.8rem' }}><button className="btn sm" onClick={save}>Save update</button> <small>{m}</small></div>
  </div>)
}

function OrdersTab() {
  const [list, setList] = useState(null)
  const load = () => api.get('/admin/orders').then((r) => setList(r.data))
  useEffect(() => { load() }, [])
  return (<div>
    <div className="row"><h2>Orders</h2><a className="btn ghost sm" href="/api/admin/orders/export.xlsx">Download Excel</a></div>
    {list && !list.length && <div className="empty">No paid orders yet.</div>}
    {list?.map((o) => <OrderRow key={o.id + o.order_status} o={o} reload={load} />)}
  </div>)
}

function ProductsTab() {
  const [list, setList] = useState([]); const [sizes, setSizes] = useState([])
  const [f, setF] = useState({ name: '', price: '', description: '', category: 'Dresses' })
  const [stock, setStock] = useState({}); const [files, setFiles] = useState([]); const [m, setM] = useState(''); const [bad, setBad] = useState('')
  const load = () => api.get('/admin/products').then((r) => setList(r.data))
  useEffect(() => { load(); api.get('/sizes').then((r) => setSizes(r.data)) }, [])
  const add = async (e) => {
    e.preventDefault(); setBad(''); setM('')
    const fd = new FormData(); Object.entries(f).forEach(([k, v]) => fd.append(k, v))
    fd.append('sizes', JSON.stringify(Object.fromEntries(Object.entries(stock).filter(([, v]) => +v > 0))))
    files.forEach((x) => fd.append('images', x))
    try { await api.post('/admin/products', fd); setM('Product added'); setF({ name: '', price: '', description: '', category: 'Dresses' }); setStock({}); setFiles([]); e.target.reset(); load() }
    catch (x) { setBad(err(x)) }
  }
  const toggle = async (p) => { await api.patch(`/admin/products/${p.id}`, { active: !p.active }); load() }
  return (<div>
    <h2>Add product</h2>
    <form className="box" onSubmit={add}>
      <label>Name</label><input required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
      <div className="two">
        <div><label>Price (₹)</label><input required type="number" min="1" value={f.price} onChange={(e) => setF({ ...f, price: e.target.value })} /></div>
        <div><label>Category</label><input value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })} /></div>
      </div>
      <label>Description</label><textarea rows="3" value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} />
      <label>Photos (you can pick several)</label><input type="file" accept="image/*" multiple onChange={(e) => setFiles([...e.target.files])} />
      <label>Stock per age size (leave 0 if not available)</label>
      <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill,minmax(110px,1fr))', gap: '.6rem' }}>
        {sizes.map((s) => <div key={s.id}><small>{s.label}</small><input type="number" min="0" value={stock[s.id] || ''} placeholder="0" onChange={(e) => setStock({ ...stock, [s.id]: e.target.value })} /></div>)}
      </div>
      {bad && <div className="err">{bad}</div>}{m && <div className="ok">{m}</div>}
      <div style={{ marginTop: '1rem' }}><button className="btn">Add product</button></div>
    </form>
    <h2>All products</h2>
    <table><tbody>{list.map((p) => (<tr key={p.id}>
      <td>{p.images[0] && <img src={p.images[0]} alt="" width="40" height="50" style={{ objectFit: 'cover' }} />}</td>
      <td>{p.name}<br /><small>{p.sizes.map((s) => `${s.label}: ${s.stock}`).join(' | ')}</small></td>
      <td>{inr(p.price)}</td>
      <td><button className="btn ghost sm" onClick={() => toggle(p)}>{p.active ? 'Hide from shop' : 'Show in shop'}</button></td>
    </tr>))}</tbody></table>
  </div>)
}
