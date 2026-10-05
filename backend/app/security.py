import bcrypt, jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from .config import settings
from .db import SessionLocal
from .models import User

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def hash_pw(p: str) -> str: return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
def check_pw(p: str, h: str) -> bool: return bcrypt.checkpw(p.encode(), h.encode())

def set_session(resp: Response, user: User):
    token = jwt.encode({"sub": str(user.id), "exp": datetime.utcnow() + timedelta(days=7)}, settings.JWT_SECRET, "HS256")
    resp.set_cookie("token", token, httponly=True, samesite="lax", secure=settings.COOKIE_SECURE, max_age=7*86400)

def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    t = request.cookies.get("token")
    try: uid = int(jwt.decode(t, settings.JWT_SECRET, ["HS256"])["sub"])
    except Exception: raise HTTPException(401, "Please log in")
    u = db.get(User, uid)
    if not u: raise HTTPException(401, "Please log in")
    return u

def admin_user(u: User = Depends(current_user)) -> User:
    if u.role != "ADMIN": raise HTTPException(403, "Admin only")
    return u
