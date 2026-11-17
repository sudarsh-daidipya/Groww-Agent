from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from backend.config import settings

router = APIRouter(prefix="/api/auth", tags=["Auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
def login(payload: LoginRequest, request: Request):
    if payload.username == settings.APP_USERNAME and payload.password == settings.APP_PASSWORD:
        request.session["authenticated"] = True
        request.session["user"] = payload.username
        return {"status": "ok"}
    raise HTTPException(status_code=401, detail="Invalid username or password")

@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"status": "logged_out"}