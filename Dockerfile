# Stage 1: Builder
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
      libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
      libffi-dev shared-mime-info postgresql-client \
      fonts-dejavu-core fonts-liberation curl \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/* && rm -rf /wheels
RUN useradd -m -u 1000 appuser
WORKDIR /app
COPY --chown=appuser:appuser . .

# Verzeichnisse für persistente Volumes (Coolify: Storages-Tab) müssen VOR
# dem USER-Wechsel angelegt/chown't werden: appuser darf sonst nicht in
# /app schreiben, da WORKDIR das Verzeichnis noch als root:root erstellt
# hat (Ursache eines "Permission denied" beim Build).
RUN mkdir -p /app/instance /app/uploads && chown -R appuser:appuser /app/instance /app/uploads

USER appuser
ENV FLASK_APP=app.py PYTHONUNBUFFERED=1
EXPOSE 5000

# Read-Only Filesystem (außer /tmp, /app/instance, /app/uploads)
VOLUME /app/instance
VOLUME /app/uploads

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -fsS http://localhost:5000/health || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "--chdir", "/app", "wsgi:app"]