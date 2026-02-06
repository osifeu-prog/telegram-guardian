# ROOT_DOCKERFILE__TG_GUARDIAN__V1
FROM python:3.11-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY web_portal/ ./web_portal/
WORKDIR /app/web_portal

RUN pip install --no-cache-dir -r requirements.txt

CMD ["sh","-c","echo BOOT_OK__ROOT_DOCKERFILE && (python -m alembic -c alembic.ini upgrade head || echo 'WARN: alembic failed') && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]