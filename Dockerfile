# ROOT_DOCKERFILE__TG_GUARDIAN__V3
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Build marker (no secrets) + make it available at runtime
ARG BUILD_MARKER=2026-02-07T00:00:00Z
ENV APP_BUILD_STAMP=$BUILD_MARKER

# deps
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# code + alembic
COPY web_portal/app ./app
COPY web_portal/alembic.ini ./alembic.ini
COPY web_portal/alembic ./alembic

RUN echo "BUILD_MARKER=$APP_BUILD_STAMP" > /app/.build_marker

CMD ["sh","-c","echo BOOT_OK__ROOT_DOCKERFILE_V3 stamp=$APP_BUILD_STAMP && (python -m alembic -c alembic.ini upgrade head || echo 'WARN: alembic failed') && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]