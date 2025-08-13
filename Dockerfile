FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY app /app/app
COPY .env /app/.env
RUN pip install --no-cache-dir fastapi uvicorn[standard] pydantic pydantic-settings python-dotenv pytz numpy pyswisseph psycopg[binary] kerykeion

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
