from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.sessions import SessionMiddleware

from backend.config import BASE_DIR, settings
from backend.services.risk import init_db
from backend.api import market, signals, bot, orders, auth
from backend.api.auth import verify_auth_token

app = FastAPI(title="Groww + Multi-AI Algo Trader")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(SessionMiddleware, secret_key=settings.APP_SECRET_KEY, max_age=86400, same_site="lax", https_only=False)

init_db()

def require_auth(request: Request):
    if request.session.get("authenticated"):
        return
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        if verify_auth_token(auth_header.split(" ", 1)[1].strip()):
            return
    raise HTTPException(status_code=401, detail="Unauthorized. Please sign in.")

app.include_router(auth.router)
app.include_router(market.router, dependencies=[Depends(require_auth)])
app.include_router(signals.router, dependencies=[Depends(require_auth)])
app.include_router(bot.router, dependencies=[Depends(require_auth)])
app.include_router(orders.router, dependencies=[Depends(require_auth)])

frontend_dir = BASE_DIR / "frontend"
app.mount("/src", StaticFiles(directory=frontend_dir / "src"), name="src")

NO_CACHE = {"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}

@app.get("/login")
def serve_login():
    return FileResponse(frontend_dir / "login.html", headers=NO_CACHE)

@app.get("/")
def serve_dashboard():
    return FileResponse(frontend_dir / "index.html", headers=NO_CACHE)
