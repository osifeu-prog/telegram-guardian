# WEB_PORTAL_DOCKERFILE_V3 (Root Directory = web_portal)
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# bring code (app/, alembic/, alembic.ini, etc.)
COPY . .

# Run migrations then start API (Railway provides $PORT)
CMD ["sh","-c","echo BOOT_OK && python -m alembic -c alembic.ini upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]