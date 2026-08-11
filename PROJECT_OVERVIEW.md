# PROJECT_OVERVIEW.md

**Generiert am**: 2026-08-11 04:22:38

---

## 🎯 Projektziel

Flask-basierte Web-Applikation für **Stärkenanalyse** mit KI-gestützter Berichterstellung:
- Teilnehmermanagement in Gruppen
- Dateneingabe (Beobachtungen, Selbsteinschätzungen)
- KI-Analyse via Mistral API
- PDF-Berichte generieren

---

## 📊 Projektstatistik

- **Python-Dateien**: 97
- **Blueprints**: 5 (groups, participants, analysis, data_io, prompts)
- **Templates**: 30
- **Datenbank-Models**: 0

---

## 🔗 Routing-Übersicht

| Blueprint | Routen-Anzahl | Zweck |
|-----------|---------------|-------|
| groups | 4 | Gruppenverwaltung |
| participants | 6 | Teilnehmerverwaltung |
| analysis | 9 | KI-Analyse & Berichte |
| data_io | 10 | Import/Export, Dateneingabe |
| prompts | 7 | Prompt-Management |

---

## 🧩 Modul-Abhängigkeiten

**app.py importiert**:
- extensions (db, migrate)
- models (Group, Participant, Prompt)
- blueprints (alle 5)

**Blueprints importieren**:
- models.py (für ORM-Queries)
- extensions.py (für db.session)
- ki_services.py (nur analysis.py)
- utils.py (nur analysis.py)

**Keine zirkulären Abhängigkeiten detected** ✅

---

## 🛠️ Entwicklungsumgebung

**Voraussetzungen**:
- Python 3.12.12
- venv: `/home/timok/kDrive/Dokumente/staerkenanalyse-app/venv`
- System-Dependencies: libcairo, libpango (für WeasyPrint)

**Setup-Schritte**:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # API-Keys eintragen
flask db upgrade
python app.py
```

---

## 🔐 Security Considerations

1. **API Keys in .env** (nicht in Git!)
2. **SECRET_KEY**: Aktuell `os.urandom(24)` → Für Production: Persistente Key in .env
3. **Debug-Modus**: Für Production deaktivieren
4. **SQLite**: Für Production → PostgreSQL migrieren

---

**Für detaillierte Informationen siehe [CONTEXT.md](CONTEXT.md)**
