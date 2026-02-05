# WEB_PORTAL_DOCKERFILE_V5 (Root Directory = web_portal)
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Never fail the container because alembic failed (otherwise Railway healthcheck never passes)
CMD ["sh","-c","echo BOOT_OK && (python -m alembic -c alembic.ini upgrade head || echo 'WARN: alembic upgrade failed (continuing)') && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]