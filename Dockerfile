FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY web_portal ./web_portal

# Don't crash the whole service if migrations fail momentarily.
CMD ["sh","-c","if [ -f web_portal/alembic.ini ]; then alembic -c web_portal/alembic.ini upgrade head || echo 'WARN: alembic upgrade failed (continuing)'; else echo 'WARN: missing web_portal/alembic.ini'; fi; uvicorn web_portal.app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
# deploy-bump 2026-02-05T19:28:01

