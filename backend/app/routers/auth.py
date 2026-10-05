import secrets, smtplib, re
from datetime import datetime, timedelta
from email.message import EmailMessage
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from ..config import settings
from ..models import User, Otp
from ..security import get_db, hash_pw, check_pw, set_session, current_user

router = APIRouter(prefix="/auth", tags=["auth"])

def send_mail(to: str, subject: str, body: str):
    if not settings.SMTP_HOST:
        print(f"[DEV EMAIL] to={to} | {subject} | {body}", flush=True)  # visible in `docker compose logs backend`
        return
    m = EmailMessage(); m["From"] = settings.SMTP_FROM or settings.SMTP_USER; m["To"] = to; m["Subject"] = subject; m.set_content(body)
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as s:
        s.starttls(); s.login(settings.SMTP_USER, settings.SMTP_PASS); s.send_message(m)

def send_otp(db: Session, email: str, purpose: str):
    last = db.query(Otp).filter_by(email=email, purpose=purpose).order_by(Otp.id.desc()).first()
    if last and (datetime.utcnow() - last.created_at).total_seconds() < 30:
        raise HTTPException(429, "Please wait 30 seconds before requesting another OTP")
    code = f"{secrets.randbelow(1000000):06d}"
    db.query(Otp).filter_by(email=email, purpose=purpose).delete()
    db.add(Otp(email=email, purpose=purpose, code_hash=hash_pw(code), expires_at=datetime.utcnow() + timedelta(minutes=5)))
    db.commit()
    send_mail(email, "Your Dheera Littles OTP", f"Your OTP is {code}. It is valid for 5 minutes.")

def check_otp(db: Session, email: str, purpose: str, code: str):
    o = db.query(Otp).filter_by(email=email, purpose=purpose).order_by(Otp.id.desc()).first()
    if not o or o.expires_at < datetime.utcnow(): raise HTTPException(400, "OTP expired. Request a new one")
    if o.attempts >= 5: raise HTTPException(429, "Too many attempts. Request a new OTP")
    o.attempts += 1; db.commit()
    if not check_pw(code, o.code_hash): raise HTTPException(400, "Incorrect OTP")
    db.delete(o); db.commit()

def get_user(db, email):
    return db.query(User).filter(User.email == email.lower()).first()

class SignupIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(pattern=r"^[6-9]\d{9}$")
    password: str = Field(min_length=8)
class LoginIn(BaseModel): email: EmailStr; password: str
class EmailIn(BaseModel): email: EmailStr
class CodeIn(BaseModel): email: EmailStr; code: str
class ResetIn(BaseModel): email: EmailStr; code: str; password: str = Field(min_length=8)

def user_out(u): return {"id": u.id, "name": u.name, "email": u.email, "role": u.role}

@router.post("/signup")
def signup(d: SignupIn, db: Session = Depends(get_db)):
    email = d.email.lower(); u = get_user(db, email)
    if u and u.is_verified: raise HTTPException(400, "Email already registered. Please log in")
    if not u: u = User(email=email); db.add(u)
    u.name, u.phone, u.password_hash = d.name, d.phone, hash_pw(d.password)
    db.commit(); send_otp(db, email, "verify")
    return {"message": "OTP sent to your email"}

@router.post("/verify")
def verify(d: CodeIn, resp: Response, db: Session = Depends(get_db)):
    email = d.email.lower(); u = get_user(db, email)
    if not u: raise HTTPException(404, "Account not found")
    check_otp(db, email, "verify", d.code); u.is_verified = True; db.commit()
    set_session(resp, u); return user_out(u)

@router.post("/login")
def login(d: LoginIn, resp: Response, db: Session = Depends(get_db)):
    u = get_user(db, d.email)
    if not u or not check_pw(d.password, u.password_hash): raise HTTPException(401, "Wrong email or password")
    if not u.is_verified:
        send_otp(db, u.email, "verify"); raise HTTPException(403, "Email not verified. We sent you an OTP")
    set_session(resp, u); return user_out(u)

@router.post("/otp/request")
def otp_request(d: EmailIn, db: Session = Depends(get_db)):
    u = get_user(db, d.email)
    if u and u.is_verified: send_otp(db, u.email, "login")
    return {"message": "If the account exists, an OTP has been sent"}

@router.post("/otp/login")
def otp_login(d: CodeIn, resp: Response, db: Session = Depends(get_db)):
    u = get_user(db, d.email)
    if not u: raise HTTPException(400, "Incorrect OTP")
    check_otp(db, u.email, "login", d.code); set_session(resp, u); return user_out(u)

@router.post("/forgot")
def forgot(d: EmailIn, db: Session = Depends(get_db)):
    u = get_user(db, d.email)
    if u: send_otp(db, u.email, "reset")
    return {"message": "If the account exists, an OTP has been sent"}

@router.post("/reset")
def reset(d: ResetIn, db: Session = Depends(get_db)):
    u = get_user(db, d.email)
    if not u: raise HTTPException(400, "Incorrect OTP")
    check_otp(db, u.email, "reset", d.code); u.password_hash = hash_pw(d.password); u.is_verified = True; db.commit()
    return {"message": "Password updated. Please log in"}

@router.get("/me")
def me(u: User = Depends(current_user)): return user_out(u)

@router.post("/logout")
def logout(resp: Response): resp.delete_cookie("token"); return {"ok": True}
