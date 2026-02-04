from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import select

from .core.ops_auth import require_ops_token
from .db import SessionLocal, get_engine
from .models import Announcement, User
from .tg_webhook import router as tg_router
from .api_airdrop import router as api_router

APP_SECRET = os.environ.get("APP_SECRET", "dev-only-change-me")
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")

s = URLSafeTimedSerializer(APP_SECRET, salt="magic-link")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

app = FastAPI()

app.include_router(tg_router)
app.include_router(api_router)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    if request.url.path.startswith("/ops/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


def issue_token(email: str) -> str:
    return s.dumps({"email": email})


def verify_token(token: str, max_age_sec: int = 1800) -> str:
    data = s.loads(token, max_age=max_age_sec)
    return data["email"]


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    with SessionLocal() as db:
        q = (
            select(Announcement)
            .where(Announcement.is_published == True)
            .order_by(Announcement.published_at.desc().nullslast())
        )
        items = list(db.execute(q).scalars())
    return templates.TemplateResponse("home.html", {"request": request, "items": items})


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "msg": ""})


@app.post("/login", response_class=HTMLResponse)
def login_send(request: Request, email: str = Form(...)):
    email = email.strip().lower()
    token = issue_token(email)
    link = f"{BASE_URL}/auth?token={token}"
    return templates.TemplateResponse("login.html", {"request": request, "msg": f"Magic link (demo): {link}"})


@app.get("/auth")
def auth(token: str):
    try:
        email = verify_token(token)
    except (BadSignature, SignatureExpired):
        return RedirectResponse(url="/login", status_code=303)

    with SessionLocal() as db:
        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if not user:
            db.add(User(email=email))
        db.commit()

    return RedirectResponse(url="/", status_code=303)


# --- ops endpoints (health/ready/live) ---

@app.get("/health")
def health():
    return {"ok": True}


@app.get("/live")
def live():
    return {"ok": True}


@app.get("/ready")
def ready():
    out = {"ok": True, "db": False, "redis": None}

    # DB required
    try:
        from sqlalchemy import text
        with get_engine().connect() as c:
            c.execute(text("SELECT 1"))
        out["db"] = True
    except Exception as e:
        out["ok"] = False
        out["db_error"] = str(e)

    # Redis optional
    try:
        ru = (os.getenv("REDIS_URL") or "").strip()
        if ru:
            import redis
            r = redis.from_url(ru, decode_responses=True)
            r.ping()
            out["redis"] = True
        else:
            out["redis"] = False
    except Exception as e:
        out["redis"] = False
        out["redis_error"] = str(e)

    if not out["ok"]:
        return Response(content=json.dumps(out), status_code=503, media_type="application/json")
    return out


@app.get("/ops/db")
def ops_db(_ops: dict = Depends(require_ops_token)):
    out = {"ok": True, "db": None, "alembic_version": None}

    try:
        from sqlalchemy import text
        with get_engine().connect() as c:
            out["db"] = bool(c.execute(text("SELECT 1")).scalar())
            try:
                out["alembic_version"] = c.execute(text("SELECT version_num FROM alembic_version")).scalar()
            except Exception:
                out["alembic_version"] = None
    except Exception as e:
        out["ok"] = False
        out["error"] = str(e)

    return out


@app.get("/ops/whoami")
def ops_whoami(_ops: dict = Depends(require_ops_token)):
    return _ops