import time
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import OperationalError
from .config import settings
from .db import Base, engine, SessionLocal
from .models import User, AgeSize
from .security import hash_pw
from .routers import auth, shop, admin

app = FastAPI(title="Dheera Littles API", docs_url="/api/docs", openapi_url="/api/openapi.json")
for r in (auth.router, shop.router, admin.router):
    app.include_router(r, prefix="/api")

import os
os.makedirs("/data/uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="/data/uploads"), name="uploads")

SIZES = [("0-3 M", "Months"), ("3-6 M", "Months"), ("6-9 M", "Months"), ("9-12 M", "Months"), ("12-18 M", "Months"),
         ("18-24 M", "Months"), ("2-3 Y", "Years"), ("3-4 Y", "Years")]

@app.on_event("startup")
def startup():
    for _ in range(20):
        try: Base.metadata.create_all(engine); break
        except OperationalError: time.sleep(2)
    db = SessionLocal()
    if not db.query(AgeSize).count():
        db.add_all([AgeSize(label=l, unit=u, sort=i) for i, (l, u) in enumerate(SIZES)])
    if not db.query(User).filter_by(email=settings.ADMIN_EMAIL.lower()).first():
        db.add(User(name="Admin", email=settings.ADMIN_EMAIL.lower(), phone="", password_hash=hash_pw(settings.ADMIN_PASSWORD), role="ADMIN", is_verified=True))
    db.commit(); db.close()

@app.get("/api/health")
def health(): return {"status": "ok"}
