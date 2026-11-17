from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from backend.config import BASE_DIR, settings
from backend.services.risk import init_db
from backend.api import market, signals, bot, orders, auth

app = FastAPI(title="Groww + Multi-AI Algo Trader")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Login session middleware
app.add_middleware(SessionMiddleware, secret_key=settings.APP_SECRET_KEY, max_age=86400)

init_db()

def require_auth(request: Request):
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Unauthorized. Please login first.")

# Public Auth Route
app.include_router(auth.router)

# Protected API Routes (Only accessible after login)
app.include_router(market.router, dependencies=[Depends(require_auth)])
app.include_router(signals.router, dependencies=[Depends(require_auth)])
app.include_router(bot.router, dependencies=[Depends(require_auth)])
app.include_router(orders.router, dependencies=[Depends(require_auth)])

frontend_dir = BASE_DIR / "frontend"
app.mount("/src", StaticFiles(directory=frontend_dir / "src"), name="src")

@app.get("/login")
def serve_login(request: Request):
    if request.session.get("authenticated"):
        return RedirectResponse(url="/")
    return FileResponse(frontend_dir / "login.html")

@app.get("/")
def serve_dashboard(request: Request):
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/login")
    return FileResponse(frontend_dir / "index.html")