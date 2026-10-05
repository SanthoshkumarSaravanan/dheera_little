import { createContext, useContext, useEffect, useState } from 'react'
import { Link, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { api } from './api'
import Shop, { Product } from './pages/Shop.jsx'
import Cart from './pages/Cart.jsx'
import Account, { Orders } from './pages/Account.jsx'
import Admin from './pages/Admin.jsx'

const Ctx = createContext()
export const useApp = () => useContext(Ctx)

export default function App() {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)
  const [cart, setCart] = useState(() => JSON.parse(localStorage.getItem('cart') || '[]'))
  const nav = useNavigate()
  useEffect(() => { api.get('/auth/me').then((r) => setUser(r.data)).catch(() => {}).finally(() => setReady(true)) }, [])
  useEffect(() => localStorage.setItem('cart', JSON.stringify(cart)), [cart])
  const logout = async () => { await api.post('/auth/logout'); setUser(null); nav('/') }
  const count = cart.reduce((a, i) => a + i.qty, 0)
  if (!ready) return null
  const guard = (el, admin) => !user ? <Navigate to="/account" /> : admin && user.role !== 'ADMIN' ? <Navigate to="/" /> : el
  return (
    <Ctx.Provider value={{ user, setUser, cart, setCart }}>
      <header><div className="wrap">
        <Link to="/" className="logo">DHEERA<small>LITTLES</small></Link>
        <nav>
          <Link to="/">Shop</Link>
          <Link to="/cart">Bag ({count})</Link>
          {user ? <>
            <Link to="/orders">My orders</Link>
            {user.role === 'ADMIN' && <Link to="/admin">Admin</Link>}
            <a href="#" onClick={(e) => { e.preventDefault(); logout() }}>Log out</a>
          </> : <Link to="/account">Log in</Link>}
        </nav>
      </div></header>
      <main className="wrap">
        <Routes>
          <Route path="/" element={<Shop />} />
          <Route path="/product/:id" element={<Product />} />
          <Route path="/cart" element={<Cart />} />
          <Route path="/account" element={<Account />} />
          <Route path="/orders" element={guard(<Orders />)} />
          <Route path="/admin" element={guard(<Admin />, true)} />
        </Routes>
      </main>
      <footer>Dheera Littles. Softly made for little ones.</footer>
    </Ctx.Provider>
  )
}
