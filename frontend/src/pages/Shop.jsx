import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, inr } from '../api'
import { useApp } from '../App.jsx'

export default function Shop() {
  const [items, setItems] = useState(null)
  useEffect(() => { api.get('/products').then((r) => setItems(r.data)) }, [])
  return (<>
    <section className="hero"><div className="wrap">
      <h1>Soft clothes for little beginnings</h1>
      <p>Dresses and rompers for newborns to 4 year olds, made gentle on tiny skin. Delivered across India.</p>
    </div></section>
    {!items ? null : items.length === 0 ? <div className="empty">No dresses yet. New arrivals are coming soon.</div> :
      <div className="grid">{items.map((p) => (
        <Link key={p.id} to={`/product/${p.id}`} className="card">
          <div className="img">{p.images[0] && <img src={p.images[0]} alt={p.name} loading="lazy" />}</div>
          <div className="name">{p.name}</div><div className="price">{inr(p.price)}</div>
        </Link>))}</div>}
  </>)
}

export function Product() {
  const { id } = useParams(); const nav = useNavigate()
  const { cart, setCart } = useApp()
  const [p, setP] = useState(null); const [img, setImg] = useState(0)
  const [unit, setUnit] = useState('Months'); const [size, setSize] = useState(null); const [qty, setQty] = useState(1)
  const [msg, setMsg] = useState('')
  useEffect(() => { api.get(`/products/${id}`).then((r) => setP(r.data)).catch(() => nav('/')) }, [id])
  if (!p) return null
  const units = [...new Set(p.sizes.map((s) => s.unit))]
  const shown = p.sizes.filter((s) => s.unit === unit)
  const chosen = p.sizes.find((s) => s.size_id === size)
  const add = () => {
    if (!chosen) return setMsg('Please choose an age size')
    const rest = cart.filter((i) => !(i.product_id === p.id && i.size_id === size))
    const prev = cart.find((i) => i.product_id === p.id && i.size_id === size)
    setCart([...rest, { product_id: p.id, size_id: size, size_label: chosen.label, name: p.name, price: p.price, image: p.images[0], qty: Math.min(10, (prev?.qty || 0) + qty) }])
    nav('/cart')
  }
  return (
    <div className="cols">
      <div>
        <img className="big" src={p.images[img]} alt={p.name} />
        <div className="thumbs">{p.images.map((s, i) => <img key={s} src={s} alt="" className={i === img ? 'on' : ''} onClick={() => setImg(i)} />)}</div>
      </div>
      <div>
        <h2>{p.name}</h2><div className="price" style={{ fontSize: '1.3rem' }}>{inr(p.price)}</div>
        <p>{p.description}</p>
        <label>Age in</label>
        <div className="seg">{units.map((u) => <button key={u} className={'chip' + (u === unit ? ' on' : '')} onClick={() => { setUnit(u); setSize(null) }}>{u}</button>)}</div>
        <label>Size</label>
        <div className="seg">{shown.map((s) => <button key={s.size_id} disabled={s.stock < 1} className={'chip' + (s.size_id === size ? ' on' : '')} onClick={() => setSize(s.size_id)}>{s.label}</button>)}</div>
        {chosen && chosen.stock <= 3 && <p style={{ color: 'var(--pink-d)' }}>Only {chosen.stock} left</p>}
        <label>Quantity</label>
        <select value={qty} onChange={(e) => setQty(+e.target.value)} style={{ width: 90 }}>{[1, 2, 3, 4, 5].map((n) => <option key={n}>{n}</option>)}</select>
        {msg && <div className="err">{msg}</div>}
        <div style={{ marginTop: '1.4rem' }}><button className="btn" onClick={add}>Add to bag</button></div>
      </div>
    </div>)
}
