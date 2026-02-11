# GitHub Actions Setup Guide

**Zuletzt geprüft:** 2026-02-11

## 🚀 Schnellstart

Diese Anleitung erklärt, wie du die GitHub Actions Workflows für das Stärkenanalyse-App-Projekt einrichtest.

---

## 📋 Voraussetzungen

1. **GitHub Repository**
   - Repository muss auf GitHub existieren
   - Du benötigst Admin-Rechte

2. **Mistral AI Account**
   - Erstelle Account auf https://console.mistral.ai/
   - Generiere API Key unter "API Keys"

3. **Lokale Entwicklungsumgebung**
   - Python 3.11+
   - Git konfiguriert
   - `.env`-Datei mit `MISTRAL_API_KEY`

---

## 🔐 Schritt 1: GitHub Secrets einrichten

### 1.1 Navigiere zu Repository Settings
```
GitHub Repository → Settings → Secrets and variables → Actions
```

### 1.2 Füge MISTRAL_API_KEY hinzu
1. Klicke auf **"New repository secret"**
2. **Name**: `MISTRAL_API_KEY`
3. **Secret**: Dein Mistral API Key (kopiere aus `.env`)
4. Klicke **"Add secret"**

✅ `GITHUB_TOKEN` ist automatisch verfügbar - keine Konfiguration nötig!

---

## 📂 Schritt 2: Workflows aktivieren

Die Workflows sind bereits in `.github/workflows/` vorhanden und werden automatisch aktiv, sobald du sie zu GitHub pushst.

### 2.1 Erste Push-Vorbereitung
```bash
# Stelle sicher, dass alle Dateien commited sind
git add .github/
git add .env.example
git add README.md

# Committe die Änderungen
git commit -m "✨ Füge GitHub Actions Workflows hinzu"

# Pushe zu GitHub
git push origin feature/postgresql-migration
```

### 2.2 Workflows in GitHub Actions Tab prüfen
1. Gehe zu deinem Repository auf GitHub
2. Klicke auf Tab **"Actions"**
3. Du solltest folgende Workflows sehen:
   - ✅ CI - Code Quality
   - ✅ Context Generator
   - ✅ AI Code Review (läuft nur bei PRs)
   - ✅ Documentation Updater

---

## 🧪 Schritt 3: Workflows testen

### 3.1 Teste Context Generator (manuell)
1. Gehe zu **Actions** → **Context Generator**
2. Klicke **"Run workflow"** → **"Run workflow"**
3. Warte ~30 Sekunden
4. Ein neuer PR sollte erstellt werden: **"🤖 Automatische Dokumentations-Aktualisierung"**
5. Review den PR → Merge ihn manuell

### 3.2 Teste CI Quality Check
```bash
# Mache eine kleine Änderung
echo "# Test" >> README.md

# Committe und pushe
git add README.md
git commit -m "test: Trigger CI"
git push
```

→ Gehe zu **Actions** Tab → **CI - Code Quality** sollte laufen

### 3.3 Teste AI Code Review
1. Erstelle einen Pull Request von `feature/postgresql-migration` → `main`
2. Gehe zu **Actions** Tab
3. **AI Code Review** sollte automatisch laufen
4. Nach ~1-2 Minuten erscheint ein Kommentar im PR mit dem Review

---

## 🔧 Schritt 4: Workflow-Anpassungen (optional)

### 4.1 Ändere Trigger-Branches

**Datei**: `.github/workflows/ci-quality.yml`

```yaml
on:
  push:
    branches: [main, feature/*, develop]  # Füge weitere Branches hinzu
```

### 4.2 Limitiere AI Review auf bestimmte Files

**Datei**: `.github/workflows/ai-code-review.yml`

```yaml
on:
  pull_request:
    paths:
      - 'blueprints/*.py'  # Nur Blueprints reviewen
      - 'models.py'
      - 'app.py'
```

### 4.3 Ändere Mistral-Modell

**Datei**: `.github/workflows/ai-code-review.yml` (Zeile ~60)

```python
response = client.chat(
    model="mistral-medium-latest",  # Günstiger als mistral-large
    # oder: "mistral-small-latest"
    ...
)
```

---

## 📊 Schritt 5: Workflow-Überwachung

### 5.1 Workflow-Status-Badges (optional)

Füge zu README.md hinzu:

```markdown
## Status

![CI Status](https://github.com/USERNAME/REPO/actions/workflows/ci-quality.yml/badge.svg)
![Context Generator](https://github.com/USERNAME/REPO/actions/workflows/context-generator.yml/badge.svg)
```

Ersetze `USERNAME/REPO` mit deinen Werten.

### 5.2 Workflow-Notifications

**GitHub Settings** → **Notifications** → **Actions**
- ✅ Aktiviere Benachrichtigungen bei Workflow-Fehlern

---

## 🐛 Troubleshooting

### Problem: Workflow schlägt fehl mit "MISTRAL_API_KEY not found"

**Lösung**:
1. Prüfe ob Secret in Repository Settings → Secrets existiert
2. Secret-Name MUSS exakt `MISTRAL_API_KEY` sein (case-sensitive!)
3. Re-run Workflow nach Secret-Hinzufügung

### Problem: AI Code Review postet keinen Kommentar

**Lösung**:
1. Prüfe Actions-Log für Fehler
2. Stelle sicher, dass PR auf `main`-Branch gerichtet ist
3. Mindestens eine `.py`-Datei muss geändert sein

### Problem: Context Generator erstellt keinen PR

**Mögliche Ursachen**:
1. `CONTEXT.md` / `PROJECT_OVERVIEW.md` sind bereits aktuell
2. `peter-evans/create-pull-request@v6` Action fehlt
3. Branch-Protection-Rules verhindern automatische PRs

**Lösung**:
- Prüfe Actions-Log im "Check for Changes" Step
- Deaktiviere Branch-Protection temporär für Test

### Problem: "Permission denied" bei PR-Erstellung

**Lösung**:
```yaml
# In Workflow-Datei:
permissions:
  contents: write  # Benötigt zum Erstellen von Commits
  pull-requests: write  # Benötigt zum Erstellen von PRs
```

---

## 🎯 Best Practices

### 1. Branch-Strategie
- **main**: Production-Code, geschützt
- **feature/***: Neue Features, CI läuft automatisch
- **hotfix/***: Dringende Fixes

### 2. PR-Workflow
1. Erstelle Feature-Branch von `main`
2. Entwickle lokal
3. Pushe zu GitHub → CI läuft
4. Erstelle PR → AI Review läuft
5. Review PRs (von Workflows + manuelle Reviews)
6. Merge nach `main`

### 3. Mistral API Kosten im Blick behalten
- Check Mistral Console regelmäßig
- Bei vielen PRs: Reduziere max_tokens in Workflow
- Alternative: Nutze `mistral-small-latest` statt `large`

### 4. CONTEXT.md aktuell halten
- Lasse Context Generator regelmäßig laufen
- Merge Context-Update-PRs zeitnah
- Bei größeren Refactorings: Manuell triggern

---

## 📚 Weiterführende Dokumentation

- **GitHub Actions Docs**: https://docs.github.com/en/actions
- **Mistral AI Docs**: https://docs.mistral.ai/
- **peter-evans/create-pull-request**: https://github.com/peter-evans/create-pull-request

---

## 🆘 Support

Bei Problemen:
1. Prüfe Actions-Logs auf GitHub
2. Validiere Secrets in Repository Settings
3. Teste Mistral API Key lokal mit:
   ```bash
   python -c "from mistralai.client import MistralClient; client = MistralClient(api_key='YOUR_KEY'); print('OK')"
   ```

---

**Viel Erfolg mit GitHub Actions! 🚀**
