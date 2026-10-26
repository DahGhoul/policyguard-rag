FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev curl fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash --uid 10001 policyrag

WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip wheel && pip install -r requirements.txt

COPY --chown=policyrag:policyrag app ./app
RUN mkdir -p /app/storage/reports /app/storage/policies && chown -R policyrag:policyrag /app/storage

USER policyrag
EXPOSE 8000

HEALTHCHECK --interval=20s --timeout=10s --start-period=15s --retries=3 \
  CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
