# Dockerfile für Stärkenanalyse Flask App
FROM python:3.12-slim

# Arbeitsverzeichnis erstellen
WORKDIR /app

# System-Dependencies für WeasyPrint und PostgreSQL
RUN apt-get update && apt-get install -y \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Requirements kopieren und installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App-Code kopieren
COPY . .

# Uploads-Verzeichnis erstellen
RUN mkdir -p uploads

# Port exposieren
EXPOSE 5000

# Umgebungsvariablen
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/health')" || exit 1

# Startbefehl (mit Gunicorn für Production)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:app"]
