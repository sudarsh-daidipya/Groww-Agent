from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from backend.config import settings

router = APIRouter(prefix="/api/auth", tags=["Auth"])

class GoogleTokenRequest(BaseModel):
    credential: str

@router.get("/config")
def get_auth_config():
    return {"client_id": settings.GOOGLE_CLIENT_ID}

@router.post("/google")
def google_login(payload: GoogleTokenRequest, request: Request):
    try:
        idinfo = id_token.verify_oauth2_token(
            payload.credential,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
        email = idinfo.get("email", "").lower()
        name = idinfo.get("name", email)

        if not idinfo.get("email_verified"):
            raise HTTPException(status_code=401, detail="Google email not verified.")

        # Whitelist check (agar ALLOWED_EMAILS set hai toh sirf wahi allow honge)
        if settings.ALLOWED_EMAILS and email not in settings.ALLOWED_EMAILS:
            raise HTTPException(status_code=403, detail=f"Access denied for {email}")

        request.session["authenticated"] = True
        request.session["user"] = name
        request.session["email"] = email
        return {"status": "ok", "user": name, "email": email}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Google token verification failed: {str(e)}")

@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"status": "logged_out"}