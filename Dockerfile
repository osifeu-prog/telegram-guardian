# ROOT_DOCKERFILE__TG_GUARDIAN__V5
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

ARG BUILD_MARKER=dev
ENV APP_BUILD_STAMP=20260210-204716
COPY web_portal/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY web_portal/app ./app
COPY web_portal/alembic.ini ./alembic.ini
COPY web_portal/alembic ./alembic

RUN echo "BUILD_MARKER=$APP_BUILD_STAMP" > /app/.build_marker

CMD ["sh","-c","echo BOOT_OK__ROOT_DOCKERFILE_V5 stamp=$APP_BUILD_STAMP && (python -m alembic -c /app/alembic.ini upgrade head || echo 'WARN: alembic failed') && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]