# ROOT_DOCKERFILE__TG_GUARDIAN__V2
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install deps first for better caching
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Runtime code layout MUST match Railway logs: /app/app/main.py
COPY web_portal/app ./app
COPY web_portal/alembic.ini ./alembic.ini
COPY web_portal/alembic ./alembic

# Harmless build marker to force rebuilds without secrets
ARG BUILD_MARKER=2026-02-07T00:00:00Z
RUN echo "BUILD_MARKER=$BUILD_MARKER" > /app/.build_marker

CMD ["sh","-c","echo BOOT_OK__ROOT_DOCKERFILE_V2 && (python -m alembic -c alembic.ini upgrade head || echo 'WARN: alembic failed') && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]