import axios from 'axios'
export const api = axios.create({ baseURL: '/api', withCredentials: true })
export const err = (e) => {
  const d = e?.response?.data?.detail
  if (Array.isArray(d)) return d.map((x) => `${x.loc?.slice(-1)[0]}: ${x.msg}`).join(', ')
  return d || 'Something went wrong. Please try again'
}
export const inr = (n) => '₹' + Number(n).toLocaleString('en-IN')
export const STATUS = { PENDING_PAYMENT: 'Awaiting payment', PLACED: 'Placed', CONFIRMED: 'Confirmed', PACKED: 'Packed', SHIPPED: 'Shipped', OUT_FOR_DELIVERY: 'Out for delivery', DELIVERED: 'Delivered', CANCELLED: 'Cancelled' }
