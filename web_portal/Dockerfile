# WEB_PORTAL_DOCKERFILE_STABLE_V1  (Railway Root Directory = web_portal)
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# bring code (app/, alembic/, alembic.ini, etc.)
COPY . .

# Migrate then run API
CMD ["sh","-c","python -m alembic -c alembic.ini upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]