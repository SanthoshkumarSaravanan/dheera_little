import io, json, uuid, os
from datetime import datetime
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from PIL import Image, ImageOps
from openpyxl import Workbook
from sqlalchemy.orm import Session
from ..models import Order, Product, ProductSize
from ..security import get_db, admin_user
from .shop import order_out, product_out, add_history

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(admin_user)])
UPLOAD_DIR = "/data/uploads"
STATUSES = ["PLACED", "CONFIRMED", "PACKED", "SHIPPED", "OUT_FOR_DELIVERY", "DELIVERED", "CANCELLED"]

@router.get("/orders")
def orders(status: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Order).filter(Order.payment_status == "PAID")
    if status: q = q.filter(Order.order_status == status)
    return [order_out(o) for o in q.order_by(Order.id.desc())]

class StatusIn(BaseModel):
    order_status: str; courier: str | None = None; tracking_no: str | None = None; note: str = ""

@router.patch("/orders/{oid}")
def update_order(oid: int, d: StatusIn, db: Session = Depends(get_db)):
    o = db.get(Order, oid)
    if not o or d.order_status not in STATUSES: raise HTTPException(400, "Invalid order or status")
    if d.order_status == "SHIPPED" and not (d.courier and d.tracking_no): raise HTTPException(400, "Enter courier and tracking number")
    if d.courier is not None: o.courier = d.courier
    if d.tracking_no is not None: o.tracking_no = d.tracking_no
    if d.order_status != o.order_status: add_history(db, o, d.order_status, d.note)
    db.commit(); return order_out(o)

@router.get("/orders/export.xlsx")
def export(db: Session = Depends(get_db)):
    wb = Workbook(); ws = wb.active; ws.title = "Orders"
    ws.append(["Order ID", "Date", "Customer", "Email", "Phone", "Address", "Items", "Total (INR)", "Payment", "Status", "Courier", "Tracking No"])
    for o in db.query(Order).filter(Order.payment_status == "PAID").order_by(Order.id):
        a = o.address
        ws.append([o.id, o.created_at.strftime("%Y-%m-%d %H:%M"), a["name"], o.user.email, a["phone"],
                   f'{a["line1"]} {a.get("line2","")}, {a["city"]}, {a["state"]} - {a["pincode"]}',
                   "; ".join(f"{i.name} ({i.size_label}) x{i.qty}" for i in o.items), o.total, o.payment_status, o.order_status, o.courier, o.tracking_no])
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    fn = f"orders-{datetime.utcnow():%Y%m%d}.xlsx"
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": f"attachment; filename={fn}"})

@router.get("/products")
def products(db: Session = Depends(get_db)):
    return [product_out(p) for p in db.query(Product).order_by(Product.id.desc())]

def save_image(f: UploadFile) -> str:
    try: img = ImageOps.exif_transpose(Image.open(f.file)).convert("RGB")
    except Exception: raise HTTPException(400, f"{f.filename} is not a valid image")
    img.thumbnail((1200, 1200)); name = f"{uuid.uuid4().hex}.jpg"
    os.makedirs(UPLOAD_DIR, exist_ok=True); img.save(os.path.join(UPLOAD_DIR, name), "JPEG", quality=82, optimize=True)
    return f"/uploads/{name}"

@router.post("/products")
def create_product(name: str = Form(...), price: int = Form(..., gt=0), description: str = Form(""), category: str = Form("Dresses"),
                   sizes: str = Form("{}"), images: list[UploadFile] = File(default=[]), db: Session = Depends(get_db)):
    """sizes = JSON like {"1": 5, "2": 3}  (age_size_id -> stock)"""
    p = Product(name=name, price=price, description=description, category=category, images=[save_image(f) for f in images if f.filename])
    p.sizes = [ProductSize(size_id=int(k), stock=int(v)) for k, v in json.loads(sizes).items()]
    db.add(p); db.commit(); return product_out(p)

class ProductPatch(BaseModel):
    active: bool | None = None; price: int | None = None; sizes: dict[str, int] | None = None

@router.patch("/products/{pid}")
def patch_product(pid: int, d: ProductPatch, db: Session = Depends(get_db)):
    p = db.get(Product, pid)
    if not p: raise HTTPException(404, "Not found")
    if d.active is not None: p.active = d.active
    if d.price: p.price = d.price
    if d.sizes is not None:
        existing = {s.size_id: s for s in p.sizes}
        for k, v in d.sizes.items():
            if int(k) in existing: existing[int(k)].stock = v
            else: p.sizes.append(ProductSize(size_id=int(k), stock=v))
    db.commit(); return product_out(p)
