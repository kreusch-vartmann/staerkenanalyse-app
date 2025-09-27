# Stärkenanalyse-App

Eine lokale Flask-Webanwendung zur Verwaltung von Gruppen und Teilnehmenden und zur Durchführung von KI-gestützten Stärkenanalysen.

Kurze Zusammenfassung
- Backend: Flask (Blueprint-basierte Struktur in `blueprints/`)
- Datenbank: SQLite (`database.db`, Schema in `schema.sql`)
- Templates: Jinja2 Vorlagen im Ordner `templates/`
- Statische Dateien: `static/`
- KI-Integration: optional über mehrere SDKs (Google Generative AI, Mistral, OpenAI, u. a.)

Wichtig: Einige KI-Bibliotheken sind optional und/oder haben schwerere Abhängigkeiten. Sie sind in `requirements.txt` gelistet, können aber Konflikte (z. B. `protobuf` Version) mit anderen Paketen aufweisen. Siehe Abschnitt "Troubleshooting / bekannte Probleme".

## Projektstruktur (wichtigste Dateien)

- `app.py` — App-Initialisierung und zentrale Routen; registriert Blueprints
- `database.py` — DB-Verbindung und Abfragemethoden (SQLite)
- `ki_services.py` — Hilfsfunktionen für KI-Aufrufe (Modelle sind optional)
- `utils.py` — Hilfsroutinen für Dateitypen, PDFs, DOCX usw.
- `blueprints/` — modulare Routengruppen (groups, participants, analysis, data_io, prompts)
- `templates/` — Jinja2 HTML-Vorlagen für UI
- `static/` — statische Assets
- `requirements.txt` — vollständige Liste der Python-Abhängigkeiten
- `schema.sql` — SQL-Skript zur Initialisierung der Datenbank

## Voraussetzungen

- Python 3.11+ (in der Entwicklung wurde Python 3.11 / 3.13 verwendet)
- `pip`
- Optional: Systempakete für `weasyprint` und ähnliche Bibliotheken (z. B. libpango, libcairo). Wenn Sie keine PDF-Generierung benötigen, können Sie `weasyprint` weglassen.

Empfohlene Vorgehensweise: Arbeiten Sie in einer virtuellen Umgebung (`venv`).

## Schnellstart (empfohlen)

1. Repository klonen und in das Verzeichnis wechseln

```bash
git clone <repo-url>
cd staerkenanalyse-app
```

2. Virtuelle Umgebung erstellen und aktivieren

```bash
python -m venv .venv
source .venv/bin/activate
```

3. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

Hinweis: Bei Problemen mit Abhängigkeitskonflikten (siehe unten) lesen Sie bitte den Abschnitt "Troubleshooting".

4. Datenbank initialisieren

Das Projekt erwartet eine SQLite-Datenbank (`database.db`). Falls ein CLI-Kommando `flask init-db` nicht vorhanden ist, können Sie das SQL-Skript `schema.sql` verwenden:

```bash
sqlite3 database.db < schema.sql
```

Prüfen Sie anschließend `database.db` im Projektverzeichnis.

5. Anwendung starten

Sie können die App direkt starten:

```bash
# Standard (Port 5001 in app.py)
python app.py

# Alternativ mit Flask-CLI
export FLASK_APP=app.py
flask run --port 5001
```

Wenn Port 5001 bereits belegt ist, starten Sie auf einem anderen Port:

```bash
python -m flask run --port 5002
```

Öffnen Sie dann http://localhost:5001 (oder 5002) im Browser.

## Konfiguration und Umgebungsvariablen

- `FLASK_ENV` bzw. `FLASK_DEBUG` (für Debug/Prod-Modus)
- KI-Provider: Je nach eingesetzten Services benötigen Sie API-Schlüssel (z. B. `OPENAI_API_KEY`, `GOOGLE_API_KEY` usw.). Diese werden in `ki_services.py` bzw. in den Blueprints genutzt — prüfen Sie dort die genaue Erkennung und Umgebungsvariablen.

## Troubleshooting / bekannte Probleme

- Port belegt
  - Fehlermeldung: `Address already in use` → starten Sie die App auf einem anderen Port (siehe Schnellstart).

- Fehlende KI-Bibliotheken
  - Laufzeitwarnungen wie `WARNUNG: google-generativeai nicht installiert` oder `mistralai nicht installiert` bedeuten, dass die entsprechenden SDKs nicht in der Umgebung verfügbar sind. Diese Bibliotheken sind optional — die App fängt fehlende SDKs an vielen Stellen ab und deaktiviert nur die betreffenden Features.

- protobuf / Abhängigkeitskonflikte
  - `google-generativeai` und andere Google-/gRPC-Pakete hängen von `protobuf` ab. Aktuell steht in `requirements.txt` `protobuf==5.29.5`, was zu Konflikten mit anderen Paketen (z. B. ältere Streamlit-Versionen) führen kann.
  - Wenn Sie auf Konflikte stoßen, zwei Optionen:
    1. Versuchen Sie, `protobuf` auf eine kompatible 4.x-Version zu fixieren, z. B. `protobuf==4.23.4`, und `pip install -r requirements.txt --force-reinstall` auszuführen. Testen Sie sorgfältig, weil einige Packages 5.x verlangen könnten.
    2. Entfernen Sie optional die problematischen KI-Pakete aus `requirements.txt` und installieren Sie nur die für Ihre Nutzung notwendigen Bibliotheken.

- System-abhängige Bibliotheken für PDF (WeasyPrint)
  - `weasyprint` benötigt unter Linux zusätzliche Systembibliotheken (libcairo, libpango, gdk-pixbuf). Wenn PDF-Generierung nicht benötigt wird, entfernen Sie `weasyprint` aus `requirements.txt` oder installieren Sie die Systemabhängigkeiten.

## Code-Hinweise / wichtige Stellen

- `blueprints/` enthält die modularen Routen. Schauen Sie in diese Dateien, wenn Sie Features erweitern möchten:
  - `blueprints/groups.py` — Gruppen anlegen/anzeigen
  - `blueprints/participants.py` — Teilnehmer CRUD & Dateneingabe
  - `blueprints/analysis.py` — KI-Analyse-Routen
  - `blueprints/data_io.py` — Import/Export-Funktionen
  - `blueprints/prompts.py` — Verwaltung von KI-Prompts

- `database.py` enthält helper-Funktionen zum Zugriff und zur Paginierung. Falls Sie Probleme mit Such- oder Pagination-Features haben, beginnen Sie hier.

## Entwickeln & Tests

- Verwenden Sie `python -m venv .venv` und `pip install -r requirements.txt` wie oben beschrieben.
- Linter/Formatters: `black`, `flake8`, `pylint` sind in `requirements.txt` gelistet. Sie können `pre-commit`-Hooks hinzufügen, falls gewünscht.

## Nächste Schritte / Empfehlungen

1. Entfernen oder optionalisieren Sie große KI-Abhängigkeiten in `requirements.txt`, wenn Sie die App lokal mit eingeschränkten Features betreiben möchten.
2. Falls Sie PDF-Generierung benötigen, installieren Sie die Systempakete für `weasyprint` (distribution-spezifisch).
3. Fügen Sie ein CLI-Kommando `flask init-db` (oder ein kleines `manage.py`) hinzu, das `schema.sql` benutzt, damit die DB-Initialisierung benutzerfreundlicher wird.

## Kontakt

Bei Fragen oder wenn ich die `README.md` weiter anpassen soll (z. B. Beispiele für API-Nutzung, Screenshots, oder CI/CD-Integration), sag kurz Bescheid — ich kann die Datei erweitern.
