FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# bring the portal code (includes app + alembic)
COPY web_portal ./web_portal

# Railway expects listening on $PORT
CMD ["sh","-c","python -m alembic -c web_portal/alembic.ini upgrade head && uvicorn web_portal.app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]