import secrets, smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
import httpx
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from ..config import settings
from ..models import User, Otp
from ..security import get_db, hash_pw, check_pw, set_session, current_user

router = APIRouter(prefix="/auth", tags=["auth"])
PHONE = r"^[6-9]\d{9}$"

def send_mail(to: str, subject: str, body: str):
    if not settings.SMTP_HOST:
        print(f"[DEV EMAIL] to={to} | {subject} | {body}", flush=True)
        return
    m = EmailMessage(); m["From"] = settings.SMTP_FROM or settings.SMTP_USER; m["To"] = to; m["Subject"] = subject; m.set_content(body)
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as s:
        s.starttls(); s.login(settings.SMTP_USER, settings.SMTP_PASS); s.send_message(m)

def send_sms(phone: str, code: str):
    """Sends the OTP by SMS. Raises 502 if the provider rejects it."""
    prov, ok, body = settings.SMS_PROVIDER.lower(), False, ""
    try:
        if prov == "msg91":
            r = httpx.post("https://control.msg91.com/api/v5/otp", json={},
                           params={"template_id": settings.MSG91_TEMPLATE_ID, "mobile": "91" + phone, "authkey": settings.SMS_API_KEY, "otp": code}, timeout=15)
            body = r.text; ok = r.status_code == 200 and r.json().get("type") == "success"
        elif prov == "fast2sms":
            r = httpx.get("https://www.fast2sms.com/dev/bulkV2", timeout=15,
                          params={"authorization": settings.SMS_API_KEY, "route": "otp", "variables_values": code, "numbers": phone})
            body = r.text; ok = r.json().get("return") is True
    except Exception as e:
        body = str(e)
    if not ok:
        print(f"[SMS FAILED] provider={prov} response={body}", flush=True)
        raise HTTPException(502, "Could not send the SMS right now. Please try again")

def mask(p: str) -> str: return "XXXXXX" + p[-4:]

def send_otp(db: Session, u: User, purpose: str) -> str:
    last = db.query(Otp).filter_by(email=u.email, purpose=purpose).order_by(Otp.id.desc()).first()
    if last and (datetime.utcnow() - last.created_at).total_seconds() < 30:
        raise HTTPException(429, "Please wait 30 seconds before requesting another OTP")
    code = f"{secrets.randbelow(1000000):06d}"
    db.query(Otp).filter_by(email=u.email, purpose=purpose).delete()
    db.add(Otp(email=u.email, purpose=purpose, code_hash=hash_pw(code), expires_at=datetime.utcnow() + timedelta(minutes=5)))
    db.commit()
    if u.phone and settings.SMS_PROVIDER and settings.SMS_API_KEY:
        send_sms(u.phone, code)
        return f"OTP sent to mobile number {mask(u.phone)}"
    # fallback (testing, or user without a mobile number): email, or backend log if SMTP is empty
    send_mail(u.email, "Your Dheera Littles OTP", f"Your OTP is {code}. It is valid for 5 minutes.")
    return "OTP sent to your email"

def check_otp(db: Session, email: str, purpose: str, code: str):
    o = db.query(Otp).filter_by(email=email, purpose=purpose).order_by(Otp.id.desc()).first()
    if not o or o.expires_at < datetime.utcnow(): raise HTTPException(400, "OTP expired. Request a new one")
    if o.attempts >= 5: raise HTTPException(429, "Too many attempts. Request a new OTP")
    o.attempts += 1; db.commit()
    if not check_pw(code, o.code_hash): raise HTTPException(400, "Incorrect OTP")
    db.delete(o); db.commit()

def get_user(db, email): return db.query(User).filter(User.email == email.lower()).first()
def get_by_phone(db, phone): return db.query(User).filter(User.phone == phone, User.is_verified == True).first()

class SignupIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(pattern=PHONE)
    password: str = Field(min_length=8)
class LoginIn(BaseModel): email: EmailStr; password: str
class EmailIn(BaseModel): email: EmailStr
class CodeIn(BaseModel): email: EmailStr; code: str
class PhoneIn(BaseModel): phone: str = Field(pattern=PHONE)
class PhoneCodeIn(BaseModel): phone: str = Field(pattern=PHONE); code: str
class ResetIn(BaseModel): email: EmailStr; code: str; password: str = Field(min_length=8)

def user_out(u): return {"id": u.id, "name": u.name, "email": u.email, "role": u.role}
GENERIC = "If the account exists, an OTP has been sent to the registered mobile number"

@router.post("/signup")
def signup(d: SignupIn, db: Session = Depends(get_db)):
    email = d.email.lower(); u = get_user(db, email)
    if u and u.is_verified: raise HTTPException(400, "Email already registered. Please log in")
    other = get_by_phone(db, d.phone)
    if other and other.email != email: raise HTTPException(400, "This mobile number is already registered")
    if not u: u = User(email=email); db.add(u)
    u.name, u.phone, u.password_hash = d.name, d.phone, hash_pw(d.password)
    db.commit()
    return {"message": send_otp(db, u, "verify")}

@router.post("/verify")
def verify(d: CodeIn, resp: Response, db: Session = Depends(get_db)):
    u = get_user(db, d.email)
    if not u: raise HTTPException(404, "Account not found")
    check_otp(db, u.email, "verify", d.code); u.is_verified = True; db.commit()
    set_session(resp, u); return user_out(u)

@router.post("/login")
def login(d: LoginIn, resp: Response, db: Session = Depends(get_db)):
    u = get_user(db, d.email)
    if not u or not check_pw(d.password, u.password_hash): raise HTTPException(401, "Wrong email or password")
    if not u.is_verified:
        msg = send_otp(db, u, "verify"); raise HTTPException(403, f"Account not verified. {msg}")
    set_session(resp, u); return user_out(u)

@router.post("/otp/request")
def otp_request(d: PhoneIn, db: Session = Depends(get_db)):
    u = get_by_phone(db, d.phone)
    if u: send_otp(db, u, "login")
    return {"message": "If this mobile number is registered, an OTP has been sent to it"}

@router.post("/otp/login")
def otp_login(d: PhoneCodeIn, resp: Response, db: Session = Depends(get_db)):
    u = get_by_phone(db, d.phone)
    if not u: raise HTTPException(400, "Incorrect OTP")
    check_otp(db, u.email, "login", d.code); set_session(resp, u); return user_out(u)

@router.post("/forgot")
def forgot(d: EmailIn, db: Session = Depends(get_db)):
    u = get_user(db, d.email)
    if u: send_otp(db, u, "reset")
    return {"message": GENERIC}

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
