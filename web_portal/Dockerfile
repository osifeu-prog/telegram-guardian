# WEB_PORTAL_DOCKERFILE_STABLE_V2 (Root Directory = web_portal)
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh","-c","echo BOOT_OK && (python -m alembic -c alembic.ini upgrade head || echo 'WARN: alembic upgrade failed (continuing)') && exec uvicorn app.main:app --host 0.0.0.0 --port "]