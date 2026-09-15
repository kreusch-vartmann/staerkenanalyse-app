# Monitoring Setup (Prometheus + Grafana)

## 📊 Überblick
- **Prometheus**: Sammelt Metriken von der App (`/metrics`-Endpoint).
- **Grafana**: Visualisiert Metriken in Dashboards.
- **Alerts**: Benachrichtigungen bei kritischen Fehlern (z. B. KI-API-Ausfälle).

---

## ⚙️ Schritt 1: Prometheus in Coolify einrichten

### 1. Prometheus-Service zu `coolify.yml` hinzufügen
```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    type: prometheus
    ports:
      - "9090:9090"
    volumes:
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
    networks:
      - app_network

volumes:
  prometheus_data:
```

### 2. `prometheus.yml` erstellen
Erstelle eine Datei `prometheus.yml` im Projektverzeichnis:

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'staerkenanalyse-app'
    static_configs:
      - targets: ['app:5000']  # 'app' ist der Service-Name in coolify.yml
```

### 3. Prometheus in Coolify deployen
1. **Coolify-UI öffnen** → Projekt → `Add Service` → `Prometheus`.
2. **Konfiguration**:
   - **Image**: `prom/prometheus:latest`
   - **Ports**: `9090:9090`
   - **Volumes**: `prometheus_data:/prometheus`
   - **Command**: `--config.file=/etc/prometheus/prometheus.yml`
3. **`prometheus.yml` als Config-File hochladen**.
4. **Deployen**.

---

## 📈 Schritt 2: Grafana in Coolify einrichten

### 1. Grafana-Service zu `coolify.yml` hinzufügen
```yaml
services:
  grafana:
    image: grafana/grafana:latest
    type: grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
    networks:
      - app_network

volumes:
  grafana_data:
```

### 2. Grafana in Coolify deployen
1. **Coolify-UI öffnen** → Projekt → `Add Service` → `Grafana`.
2. **Konfiguration**:
   - **Image**: `grafana/grafana:latest`
   - **Ports**: `3000:3000`
   - **Volumes**: `grafana_data:/var/lib/grafana`
3. **Deployen**.

### 3. Prometheus als Datenquelle hinzufügen
1. **Grafana-UI öffnen** (z. B. `http://grafana.deine-domain.de`).
2. **Login**: Standard-Admin (`admin` / `admin`).
3. **Datenquelle hinzufügen**:
   - **Name**: `Prometheus`
   - **URL**: `http://prometheus:9090`
   - **Speichern & Testen**.

### 4. Dashboard importieren
1. **Dashboard herunterladen**: [Stärkenanalyse-Dashboard.json](./dashboards/staerkenanalyse_dashboard.json) (Beispiel-Dashboard).
2. **In Grafana importieren**:
   - **Dashboards** → **Import** → JSON-Datei hochladen.

---

## 🔔 Schritt 3: Alerts einrichten

### 1. Alert-Regeln in `prometheus.yml`
```yaml
rule_files:
  - 'alert.rules'

# alert.rules
groups:
- name: staerkenanalyse-alerts
  rules:
  - alert: KI_API_Fehler
    expr: rate(ki_api_errors_total[5m]) > 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "KI-API Fehler ({{ $labels.model }})"
      description: "Die KI-API {{ $labels.model }} meldet Fehler: {{ $value }} pro Minute."

  - alert: Hohe_Latenz
    expr: histogram_quantile(0.95, sum(rate(flask_request_latency_seconds_bucket[5m])) by (le)) > 2
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Hohe Latenz in der App"
      description: "95% der Requests dauern länger als 2 Sekunden."
```

### 2. Alertmanager in Coolify einrichten
1. **Alertmanager-Service zu `coolify.yml` hinzufügen**:
   ```yaml
   services:
     alertmanager:
       image: prom/alertmanager:latest
       ports:
         - "9093:9093"
       volumes:
         - alertmanager_data:/alertmanager
       command:
         - '--config.file=/etc/alertmanager/alertmanager.yml'
   ```
2. **`alertmanager.yml` erstellen**:
   ```yaml
   route:
     receiver: 'email'
   
   receivers:
   - name: 'email'
     email_configs:
     - to: 'admin@deine-domain.de'
       from: 'alertmanager@deine-domain.de'
       smarthost: 'smtp.deine-domain.de:587'
       auth_username: 'smtp-user'
       auth_password: 'smtp-password'
   ```
3. **Prometheus mit Alertmanager verbinden** (in `prometheus.yml`):
   ```yaml
   alerting:
     alertmanagers:
     - static_configs:
       - targets: ['alertmanager:9093']
   ```

---

## 🧪 Schritt 4: Testen

### 1. Metriken prüfen
- **Prometheus-UI**: [http://prometheus.deine-domain.de](http://prometheus.deine-domain.de)
  - Abfrage: `flask_request_count`
  - Erwartet: Metriken der App.

### 2. Dashboard prüfen
- **Grafana-UI**: [http://grafana.deine-domain.de](http://grafana.deine-domain.de)
  - Dashboard: `Stärkenanalyse-App`
  - Erwartet: Visualisierte Metriken (Requests, Latenz, KI-API-Fehler).

### 3. Alerts testen
- **KI-API-Fehler simulieren**:
  ```bash
  # Mistral-API-Key in .env löschen und App neustarten
  sed -i 's/MISTRAL_API_KEY=.*//' .env
  flask run --port 5001
  ```
- **Erwartet**: Alert in Grafana + E-Mail-Benachrichtigung.

---

## 🛠️ Troubleshooting

### Fehler: "Keine Metriken in Prometheus"
- **Lösung**: Prüfe den `/metrics`-Endpoint der App:
  ```bash
  curl http://localhost:5000/metrics
  ```
- **Erwartet**: Prometheus-Metriken (z. B. `flask_request_count`).

### Fehler: "Grafana zeigt keine Daten"
- **Lösung**: Prüfe die Prometheus-Datenquelle in Grafana:
  - **URL**: `http://prometheus:9090` (nicht `localhost`!).

### Fehler: "Alertmanager sendet keine E-Mails"
- **Lösung**: SMTP-Konfiguration prüfen:
  ```bash
  docker logs coolify-alertmanager-1
  ```