import hmac, hashlib, re, json
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from ..config import settings
from ..models import AgeSize, Product, ProductSize, Order, OrderItem, StatusHistory, User
from ..security import get_db, current_user

router = APIRouter(tags=["shop"])
LIVE = bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)

def product_out(p: Product):
    return {"id": p.id, "name": p.name, "description": p.description, "price": p.price, "category": p.category,
            "active": p.active, "images": p.images or [],
            "sizes": [{"size_id": s.size_id, "label": s.size.label, "unit": s.size.unit, "stock": s.stock}
                      for s in sorted(p.sizes, key=lambda s: s.size.sort)]}

def order_out(o: Order):
    return {"id": o.id, "created_at": o.created_at.isoformat(), "order_status": o.order_status, "payment_status": o.payment_status,
            "subtotal": o.subtotal, "shipping": o.shipping, "total": o.total, "address": o.address,
            "courier": o.courier, "tracking_no": o.tracking_no,
            "customer": {"name": o.user.name, "email": o.user.email, "phone": o.user.phone},
            "items": [{"name": i.name, "size_label": i.size_label, "qty": i.qty, "price": i.price} for i in o.items],
            "history": [{"status": h.status, "note": h.note, "at": h.created_at.isoformat()} for h in o.history]}

def add_history(db, order, status, note=""):
    order.order_status = status
    db.add(StatusHistory(order_id=order.id, status=status, note=note))

@router.get("/sizes")
def sizes(db: Session = Depends(get_db)):
    return [{"id": s.id, "label": s.label, "unit": s.unit} for s in db.query(AgeSize).order_by(AgeSize.sort)]

@router.get("/config")
def config():
    return {"shipping_flat": settings.SHIPPING_FLAT, "free_above": settings.FREE_SHIPPING_ABOVE, "payments_live": LIVE}

@router.get("/products")
def products(category: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Product).filter(Product.active == True)
    if category: q = q.filter(Product.category == category)
    return [product_out(p) for p in q.order_by(Product.id.desc())]

@router.get("/products/{pid}")
def product(pid: int, db: Session = Depends(get_db)):
    p = db.get(Product, pid)
    if not p or not p.active: raise HTTPException(404, "Product not found")
    return product_out(p)

class Item(BaseModel): product_id: int; size_id: int; qty: int = Field(ge=1, le=10)
class Address(BaseModel):
    name: str = Field(min_length=2); phone: str = Field(pattern=r"^[6-9]\d{9}$")
    line1: str = Field(min_length=3); line2: str = ""; city: str = Field(min_length=2)
    state: str = Field(min_length=2); pincode: str = Field(pattern=r"^[1-9]\d{5}$")
class OrderIn(BaseModel): items: list[Item] = Field(min_length=1); address: Address

@router.post("/orders")
async def create_order(d: OrderIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    lines, subtotal = [], 0
    for it in d.items:
        p = db.get(Product, it.product_id)
        ps = db.query(ProductSize).filter_by(product_id=it.product_id, size_id=it.size_id).first()
        if not p or not p.active or not ps: raise HTTPException(400, "An item in your cart is no longer available")
        if ps.stock < it.qty: raise HTTPException(400, f"Only {ps.stock} left of {p.name} ({ps.size.label})")
        lines.append(OrderItem(product_id=p.id, size_id=ps.size_id, name=p.name, size_label=ps.size.label, qty=it.qty, price=p.price))
        subtotal += p.price * it.qty
    shipping = 0 if subtotal >= settings.FREE_SHIPPING_ABOVE else settings.SHIPPING_FLAT
    o = Order(user_id=u.id, address=d.address.model_dump(), subtotal=subtotal, shipping=shipping, total=subtotal + shipping, items=lines)
    db.add(o); db.flush(); add_history(db, o, "PENDING_PAYMENT", "Waiting for UPI payment")
    if LIVE:
        async with httpx.AsyncClient() as c:
            r = await c.post("https://api.razorpay.com/v1/orders", auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
                             json={"amount": o.total * 100, "currency": "INR", "receipt": f"DL{o.id}"})
        if r.status_code >= 400: db.rollback(); raise HTTPException(502, "Payment gateway error. Try again")
        o.rzp_order_id = r.json()["id"]
    db.commit()
    return {"order_id": o.id, "amount": o.total, "rzp_order_id": o.rzp_order_id,
            "key_id": settings.RAZORPAY_KEY_ID if LIVE else None, "dev_mode": not LIVE}

def mark_paid(db: Session, o: Order, payment_id: str):
    if o.payment_status == "PAID": return  # idempotent (webhook + client verify)
    o.payment_status, o.rzp_payment_id = "PAID", payment_id
    for i in o.items:
        ps = db.query(ProductSize).filter_by(product_id=i.product_id, size_id=i.size_id).first()
        if ps: ps.stock = max(0, ps.stock - i.qty)
    add_history(db, o, "PLACED", "Payment received. Order placed")
    db.commit()

class VerifyIn(BaseModel): order_id: int; razorpay_payment_id: str; razorpay_signature: str

@router.post("/payments/verify")
def verify(d: VerifyIn, u: User = Depends(current_user), db: Session = Depends(get_db)):
    o = db.get(Order, d.order_id)
    if not o or o.user_id != u.id or not LIVE: raise HTTPException(404, "Order not found")
    sig = hmac.new(settings.RAZORPAY_KEY_SECRET.encode(), f"{o.rzp_order_id}|{d.razorpay_payment_id}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, d.razorpay_signature): raise HTTPException(400, "Payment verification failed")
    mark_paid(db, o, d.razorpay_payment_id); return order_out(o)

@router.post("/payments/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    sig = hmac.new(settings.RAZORPAY_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    if not settings.RAZORPAY_WEBHOOK_SECRET or not hmac.compare_digest(sig, request.headers.get("x-razorpay-signature", "")):
        raise HTTPException(400, "Bad signature")
    ev = json.loads(body)
    if ev.get("event") in ("payment.captured", "order.paid"):
        pay = ev["payload"]["payment"]["entity"]
        o = db.query(Order).filter_by(rzp_order_id=pay["order_id"]).first()
        if o: mark_paid(db, o, pay["id"])
    return {"ok": True}

@router.post("/payments/dev-confirm/{oid}")
def dev_confirm(oid: int, u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Test mode only (no Razorpay keys): simulates a successful UPI payment."""
    o = db.get(Order, oid)
    if LIVE or not o or o.user_id != u.id: raise HTTPException(404, "Not available")
    mark_paid(db, o, f"dev_{oid}"); return order_out(o)

@router.get("/orders/my")
def my_orders(u: User = Depends(current_user), db: Session = Depends(get_db)):
    qs = db.query(Order).filter_by(user_id=u.id, payment_status="PAID").order_by(Order.id.desc())
    return [order_out(o) for o in qs]
