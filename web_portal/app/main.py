from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from sqlalchemy import select

from .db import SessionLocal
from .models import User, Announcement

APP_SECRET = os.environ.get("APP_SECRET", "dev-only-change-me")
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")

s = URLSafeTimedSerializer(APP_SECRET, salt="magic-link")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

app = FastAPI()

def issue_token(email: str) -> str:
    return s.dumps({"email": email})

def verify_token(token: str, max_age_sec: int = 1800) -> str:
    data = s.loads(token, max_age=max_age_sec)
    return data["email"]

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    with SessionLocal() as db:
        q = select(Announcement).where(Announcement.is_published == True).order_by(Announcement.published_at.desc())
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

    # MVP: כרגע מציגים את הלינק על המסך (לא שולחים מייל).
    # בשלב הבא נחבר ספק מייל (Resend/Mailgun) ונשלח אותו באמת.
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
            user = User(email=email, marketing_opt_in=True)
            db.add(user)
        user.last_login_at = datetime.now(timezone.utc)
        db.commit()

    # MVP: ללא session cookie עדיין. בשלב הבא נוסיף sessions.
    return RedirectResponse(url="/", status_code=303)
