ARG CACHEBUST=25
FROM python:3.11-slim

ARG CACHEBUST
RUN echo "CACHEBUST=${CACHEBUST}" > /dev/null

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PORT=8080

ARG BUILD_MARKER=dev
ENV APP_BUILD_STAMP=20260211-131014

COPY web_portal/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
# Force install pydantic-settings to ensure it's available
RUN pip install --no-cache-dir pydantic-settings

COPY web_portal/app ./app
COPY web_portal/alembic.ini ./alembic.ini
COPY web_portal/alembic ./alembic

RUN echo "BUILD_MARKER=$APP_BUILD_STAMP" > /app/.build_marker

CMD sh -c "echo BOOT_OK__ROOT_DOCKERFILE_V5 stamp=$APP_BUILD_STAMP && exec uvicorn app.main:app --host 0.0.0.0 --port $PORT"
