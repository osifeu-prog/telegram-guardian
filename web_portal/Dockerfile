# WEB_PORTAL_ROOT_DOCKERFILE_V1
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# when Root Directory = web_portal, "." contains: app/, alembic/, alembic.ini
COPY . .

# Run migrations then start API (Railway provides $PORT)
CMD ["sh","-c","python -m alembic -c alembic.ini upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
# deploy-bump 2026-02-05T20:11:31

