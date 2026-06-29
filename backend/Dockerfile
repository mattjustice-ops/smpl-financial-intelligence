FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .
COPY scripts ./scripts
COPY templates ./templates

# Prompt 5 deck export runs Claude-generated PptxGenJS via Node (pptxgenjs in deck-gen).
RUN if [ -f scripts/deck-gen/package.json ]; then \
      cd scripts/deck-gen && npm install --omit=dev; \
    else \
      echo "WARN: scripts/deck-gen missing — Prompt 5 deck export unavailable"; \
    fi

EXPOSE 8000

# Railway (and Render) inject PORT; default 8000 for local Docker.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
