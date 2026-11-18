import sqlite3
import hashlib
import secrets
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from itsdangerous import URLSafeTimedSerializer
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from backend.config import settings, DB_PATH, IST

router = APIRouter(prefix="/api/auth", tags=["Auth"])
serializer = URLSafeTimedSerializer(settings.APP_SECRET_KEY)

def _init_users_table():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT,
            password_hash TEXT,
            auth_provider TEXT DEFAULT 'google',
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

_init_users_table()

def create_auth_token(email: str, name: str) -> str:
    return serializer.dumps({"email": email, "name": name})

def verify_auth_token(token: str):
    try:
        return serializer.loads(token, max_age=86400)
    except Exception:
        return None

def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return f"{salt}:{pwd_hash}"

def _verify_password(password: str, stored: str) -> bool:
    if not stored or ":" not in stored:
        return False
    salt, pwd_hash = stored.split(":", 1)
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return secrets.compare_digest(check, pwd_hash)

class GoogleTokenRequest(BaseModel):
    credential: str

class EmailAuthRequest(BaseModel):
    name: str = ""
    email: str
    password: str

@router.post("/google")
def google_login_or_signup(payload: GoogleTokenRequest, request: Request):
    try:
        idinfo = id_token.verify_oauth2_token(
            payload.credential,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
        email = idinfo.get("email", "").lower()
        name = idinfo.get("name", email.split("@")[0])

        if not idinfo.get("email_verified"):
            raise HTTPException(status_code=401, detail="Google email not verified.")

        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT OR IGNORE INTO users (email, name, auth_provider, created_at) VALUES (?, ?, 'google', ?)",
            (email, name, datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
        conn.close()

        token = create_auth_token(email, name)
        request.session["authenticated"] = True
        return {"status": "ok", "user": name, "email": email, "token": token}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Google verification failed: {str(e)}")

@router.post("/signup")
def email_signup(payload: EmailAuthRequest, request: Request):
    email = payload.email.strip().lower()
    if not email or len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Valid email and min 6-character password required.")
    name = payload.name.strip() or email.split("@")[0]
    conn = sqlite3.connect(DB_PATH)
    if conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Account already exists. Please Sign In.")
    conn.execute(
        "INSERT INTO users (email, name, password_hash, auth_provider, created_at) VALUES (?, ?, ?, 'email', ?)",
        (email, name, _hash_password(payload.password), datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()
    token = create_auth_token(email, name)
    request.session["authenticated"] = True
    return {"status": "ok", "user": name, "token": token}

@router.post("/login")
def email_login(payload: EmailAuthRequest, request: Request):
    email = payload.email.strip().lower()
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT name, password_hash FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=401, detail="No account found. Please Sign Up first.")
    name, pwd_hash = row
    if not pwd_hash:
        raise HTTPException(status_code=400, detail="Use 'Continue with Google' for this email.")
    if not _verify_password(payload.password, pwd_hash):
        raise HTTPException(status_code=401, detail="Incorrect password.")
    token = create_auth_token(email, name)
    request.session["authenticated"] = True
    return {"status": "ok", "user": name, "token": token}

@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"status": "logged_out"}
